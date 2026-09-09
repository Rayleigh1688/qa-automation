# 架构与维护边界

## 执行依赖

`package.json` → `python-launcher.mjs` → `run-local.py` / `config/local-commands.json` → `scripts/run-*.py` → API runner / Playwright → 原始结果 → 报告渲染器。

CLI 文件保留原路径和命令；实现按公共能力与项目业务分层：

| 位置 | 职责 | 依赖方向 |
| --- | --- | --- |
| `scripts/run-*.py`、原 API CLI | 参数和执行编排、兼容命令入口 | 调用公共能力与 FILBET 实现 |
| `scripts/qa_core/` | 环境、锁、跨平台进程、编解码、终端样式、通用报告 | 新公共模块不依赖 FILBET；旧 `contracts.py` 仅作兼容转发 |
| `scripts/filbet/` | API 请求实现、业务契约、认证/KYC/充值/流水/提现及 UI 资金支持 | 可依赖 qa_core，不动态加载业务 CLI |
| `tests/unit/` | 框架与业务实现的离线单元测试，包括开户工具回归 | `npm run test:unit` 统一发现；路径由 `support.py` 计算 |
| `ui/elements/`、`ui/framework/` | 页面操作及浏览器侧支持 | 维持当前 Playwright 组织方式 |

`filbet.controlled.ControlledFlow` 是受控业务的导入入口，每个实例持有独立的审批码、运行记录和报告状态。内部 operation 类按业务职责拆分，通过该对象协作，不单独作为 CLI。创建对象不加载凭据、不登录、不写业务数据；执行操作仍使用原环境变量和认证规则，因此不支持同一 Python 进程内并发运行多个资金流程。UI 资金支持直接创建该对象，不再动态加载受控 CLI。

`filbet/smoke.py` 保存原 API smoke 实现，`filbet/contracts.py` 保存 FILBET 路由/时间契约。`qa_core/process.py` 与 `qa_core/reporting.py` 收拢进程管理和通用报告组件；`filbet/reporting.py` 负责原资金文案和布局默认值。原 `ui_process.py`、`p0_report_template.py`、`ui_fund_flow.py`、`api_contracts.py` 及 `qa_core/contracts.py` 保留兼容导出；新代码使用规范模块路径。API 命令文件仍可按原路径执行。

跨平台要求适用于整个目录：仓库路径由 `Path(__file__)` 推导，子 Python 使用 `sys.executable`，npm/Playwright 使用公共启动能力；不在业务模块新增 shell、POSIX 锁或平台信号操作。Windows Job Object 与 POSIX 进程组仍由同一个公共模块按平台选择。本机锁和报告输出路径保持原约定。

公共包导入时不加载环境凭据、不发起业务请求。CBOR 保留原有协议子集；响应解码优先识别合法 JSON 对象/数组。

UI 用例依赖 `ui/elements/` 和 `ui/framework/`，页面、弹窗、游戏点击点与固定套件由 `ui/data/` 提供。资金链使用 uid/订单 ID/时间窗口关联执行面，认证状态不跨运行复用。

## 跨项目封装边界

`qa_core/workflow.py` 提供项目根目录、锁 namespace 和阶段参数数组；`run-local.py` 只保留 FILBET 命令清单与 CLI 解析。默认 namespace 和锁文件路径不变。独立项目选择自己的 namespace，避免无关项目互相阻塞；同项目所有 checkout 必须保持一致。

`qa_core/export.py` 的白名单是导出边界，明确排除兼容转发到业务包的 `contracts.py`、FILBET 配置与数据。新增公共模块时须同时核对依赖及独立导出测试，不通过复制整个 scripts 目录交付新项目。

## 文档归属

| 信息 | 权威入口 |
| --- | --- |
| 当前证据、有效例外、下一步 | `AI-HANDOFF.md` |
| 命令行为、写入范围 | `docs/commands.md`，实现以 CLI 为准 |
| FAT/UAT 契约与当前环境接受标准 | `api/runbooks/ENVIRONMENTS.md` |
| 可执行用例、顺序、lane | `api/p0/` 固定资产；默认 UI 清单在 `ui/data/` |
| 长期方法 | `skills/` |
| AI 任务阅读路由 | `.agents/skills/filbet-p0-automation/SKILL.md` |
| 操作步骤 | `api/runbooks/`、`ui/README.md` |
| 故障、复现及过期处理 | `harness/` |
| 阶段目标 | `testing-plan/` |
| 冻结成果 | 阶段报告、`docs/history/`、专项扫描快照 |

上层导航链接到权威文件；代码与文档不一致时先确认实际行为，再修正语义，不能把过时文档当成强制执行脚本。

## 专项资产与兼容策略

历史扫描集中在 `archive/interface-scans/2026-09-07/`，从 [归档索引](../archive/interface-scans/README.md) 阅读。保留原始脚本与数据，修正 Markdown 链接；manifest 记录搬迁前后哈希，`check:archive` 检查归档完整性。脚本仍含历史 cwd/输出路径，归档不承诺直接重跑兼容；它们不属于当前 P0 运行依赖。

本地忽略文件随目录搬迁并保持忽略，归档不自动将截图或本地数据纳入 Git。归档仅供参考，不能作为本轮门禁证据。

后续工作以 [新需求设计](../requirements/README.md) 为入口，按变更影响补用例并评估是否纳入 P0，不要求全接口自动化后再做需求测试。

受控 runner 已拆分至 `filbet/`；后续按实际需求扩展相应模块。公共核心仍在本仓库内维护，尚未发布为独立安装包；可通过白名单工具导出源码快照，能力清单、接入示例及验证边界见 [跨项目运行核心](runtime-reuse.md)。不直接复制业务目录。

## 本地校验

`npm run check` 依次执行当前文档引用/npm 命令检查、归档完整性校验、API 资产与时间单位检查、Python/JavaScript 语法检查和 runner 单元测试。它不连接业务服务，也不能证明线上渠道、账号或 CI 当前可用。

历史交接与扫描快照不作为当前导航或命令校验对象；扫描快照改由 manifest 校验保留内容。普通文档链接会校验目标文件是否存在；Markdown 锚点、自然语言规则一致性和业务有效性仍需人工审查。
