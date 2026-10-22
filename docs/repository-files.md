# 仓库文件门禁

门禁只读取本地文件和 Git 元数据，不登录业务、不查询生产、不发送通知、不删除文件，也不改写历史。公共实现位于 `scripts/qa_core/repository_files.py`；`scripts/check-repository-files.py` 只提供 CLI。规则配置见 [repository-file-policy.json](../config/repository-file-policy.json)。

## 大小与批次预算

| 范围 | 规则 |
| --- | --- |
| 单文件 | 大于等于 1 MiB 提示；大于 5 MiB 阻断；恰好 5 MiB 只提示 |
| 一批变更 | 超过 25 MiB 或 500 个不同路径提示，仍可通过；预算不是整个仓库的大小／文件数限制 |
| 禁止类别 | 无论大小均阻断，不能用 CSV 例外豁免 |

1 MiB 为 1,048,576 字节。暂存区按 Git 索引中 blob 的字节数判断，受到 `.gitattributes` 的换行归一化影响，未暂存修改不能掩盖已暂存大文件。删除不计入新增文件；重命名计目的路径一次。推送／CI 遍历范围内每个提交，包含中途加入后又删除的内容：不同路径计一次文件数，同一路径的每个不同 blob 版本分别计入字节预算，重复 ref 不重复计量。

`check:repo` 检查索引已跟踪路径在工作树中的当前文件，展示全仓统计，**不使用单批预算**。未跟踪文件在加入暂存区后由 `check:staged` 检查。工作树模式按实际文件字节计量；文件换行转换后大小可能与暂存区不同，提交判定以暂存区和 CI 的 Git blob 为准。符号链接只检查链接本身，不读取其指向文件；未检查的 Git 子模块阻断。

## 不应进入仓库的文件

- 依赖和缓存：任意层级的 `node_modules`、`.venv`、`venv`、`site-packages`、`__pycache__`、常见工具缓存等。
- 已知执行产物：根 `reports/`、任意层级 `api/results/`、`ui/results/`、`ui/reports/`、`api/local-state/`，截图／视频／Playwright 输出／coverage／日志／原始响应目录，以及 HAR、运行结果和冻结执行包快照等。仅允许既有三个 `.gitkeep` 常规文件为空或精确单个 LF 换行，不允许任意非空占位内容。
- 已退出的 `archive/interface-scans/` 原始扫描，只保留其 README。历史 blob 不因本次门禁自动删除或重写。
- 本地环境／认证状态、密钥文件、生成的 ZIP／tar 等分享包。分享包保留生成源与白名单打包器；实际包放忽略的输出目录。
- 嵌套复制的执行器／运行核心、`runtime-manifest.json`，以及同时具有 `package.json` 和仓库特征入口的嵌套整仓副本。公共核心仍可按 [现有白名单](runtime-reuse.md) 导出到其他项目，不回填到本仓库。

正式需求设计、`requirements/history/` 资料、源 CSV、正式 XMind 和选定 HTML 报告可以保留，仍受大小限制。`.xmind` 不是被禁止的分享包。规则按已知路径和文件类型识别；这不是完整敏感内容扫描器，不能证明任意重命名或压缩后的响应已经脱敏。现有 API 资产检查和人工提交审查继续生效。

## 本地使用与安装 hooks

```bash
npm run check:repo
npm run check:staged
npm run check
```

`npm run check` 已包含当前工作树门禁；默认 `check:evidence` 只查当前需求，历史来源仍可显式运行 `npm run qa -- evidence --allow-pending --include-history`。历史正式资产的可读性与业务结论仍遵循各自流程，退出默认需求扫描不代表业务验收通过。

本机安装 hooks 是明确的 Git 配置操作，由维护者执行。安装前先查看已有 `core.hooksPath`，已有其他 hooks 时应整合，避免覆盖其路由。仓库提供的文件需要保留可执行位；终端／Git 客户端须能找到 Node 和本项目 Python 解释器。

```bash
git config --get core.hooksPath
git config --local core.hooksPath .githooks
```

`pre-commit` 检查实际索引，策略也必须存在于索引中；未暂存的 CSV 例外不能批准已暂存大文件，策略缺失或冲突即失败。`pre-push` 读取 Git 提供的所有 ref 更新，覆盖分支、指向提交的标签、多 ref 更新及中间提交。仅删除远端 ref 不检查新增 blob。新分支只使用已知远端 ref／远端旧提交排除已存在历史，不用任意本地分支或 `--all` 排除尚未推送的提交。

新 ref 没有可验证的远端共同历史、浅克隆、所需 Git 对象缺失或输入不完整时，检查失败并返回非零。先正常获取完整远端历史再重试；工具不会自行联网补齐对象。首次向空远端迁移必须显式审核全部可达历史，不能用未知基线绕过检查。以下离线命令用于审查，**不会替代或自动绕过 hook**：

```bash
node scripts/python-launcher.mjs scripts/check-repository-files.py range --base <完整旧提交SHA> --head <完整新提交SHA>
node scripts/python-launcher.mjs scripts/check-repository-files.py range --root-history --head <完整新提交SHA>
```

退出码：0 为通过（可有预算／大小提示）；1 为明确阻断；2 为范围或元数据无法完整检查。所有提示只含路径、对象 ID 和大小，不输出响应／凭据内容。缺少 Node、Python 或 Git 时 hook 也会失败，不默默放行。

## CI 与历史范围

[独立 CI](../.github/workflows/repository-files.yml) 在 push／pull request 上运行：获取完整 Git 历史，执行本门禁的临时 Git 仓库单测，再按事件中的真实 base/head 检查提交。检查本身只使用本地对象，不安装业务依赖或执行业务任务；不修改已有 Telegram 通知工作流。

新建分支的 CI 以另一个远端默认分支为基线，避免 checkout 后把新分支自身当作“已存在”排除。首次默认分支推送没有可靠基线、强推后的旧对象不可读或不支持的事件都失败关闭；维护者须补齐范围并审核，不能标记为已完整检查。门禁不会对已存在基线之前的所有旧 raw blob 重复失败；如果在本轮重新加入这些文件，仍阻断。

hooks 需要本机安装，CI 是否必须通过取决于仓库分支保护。它们不构成对恶意修改检查器／工作流本身的防护；代码审查仍须核对策略和门禁变更。

## 必要源 CSV 的精确例外

当前例外表为空。只有 `api/inventory/`、`api/catalog/`、`api/p0/` 中已经评审的必要源 CSV 可以申请单文件大小例外。每项必须包含准确的 `path`、Git `blob_oid`、归一化 blob 的 `bytes` 及具体 `reason`；示意字段为 `path / blob_oid / bytes / reason`，不支持通配符、目录或整个 CSV 类型放行。

例外必须匹配同一路径、同一 Git blob 和同一字节数，内容变化即不再适用；它只免除大于 5 MiB 的阻断，仍报告所用例外并计入批次预算。禁止类别、生成结果和执行器副本不能例外。Git blob ID 与文件内容 SHA256 是不同概念；清理记录可另记 SHA256，不能拿它代替当前仓库的 Git blob ID。

push／CI 每个被检查提交使用其自身已提交的策略，多 ref 只合并判定结果，不共享例外。大 CSV 必须在引入它的同一提交包含匹配策略；未提交、更晚提交或其他 ref 的例外均不能追溯批准。门禁引入前没有策略文件的提交使用固定阈值和空例外，绝不回退读取本机策略；已有但格式不正确的策略仍失败。策略文件限制为不超过 64 KiB 的常规 JSON 文件。

可用 `git ls-tree -r -l HEAD -- <源CSV路径>` 查看已提交对象及大小，暂存内容用 `git ls-files --stage -- <源CSV路径>` 定位对象，再以 `git cat-file -s <blobID>` 获取大小。检查器不自动添加例外，也不自动把大文件迁移到 LFS。
