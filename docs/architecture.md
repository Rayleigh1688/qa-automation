# 架构与维护边界

## 执行依赖

`package.json` → `scripts/run-*.py` → API runner / Playwright → 原始结果 → 报告渲染器。

CLI 文件保留原路径和命令；共享 Python 能力集中到可直接导入的 `scripts/qa_core/` 包：

| 模块 | 职责 | 兼容方式 |
| --- | --- | --- |
| `qa_core/codec.py` | 既有 CBOR 编解码与响应 JSON 回退 | smoke runner 继续导出原函数名，受控资金链与 session 工具调用不变 |
| `qa_core/contracts.py` | 请求时间单位与动态参数解析 | `scripts/api_contracts.py` 保留兼容导出，生成器和 runner 使用新包 |

公共包导入时不加载环境凭据、不发起业务请求。CBOR 保留原有协议子集；响应解码优先识别合法 JSON 对象/数组，修复 JSON 被宽松 CBOR 解码误读并丢失业务字段的问题。

UI 用例依赖 `ui/elements/` 和 `ui/framework/`，页面、弹窗、游戏点击点与固定套件由 `ui/data/` 提供。资金链使用 uid/订单 ID/时间窗口关联执行面，认证状态不跨运行复用。

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

`api-controlled-flow-runner.py` 仍是较大的业务编排模块。后续按认证、KYC、充值、提现逐步拆分；公共基础能力已先迁入 `qa_core/`，业务步骤仍由原 runner 编排；后续拆分以现有契约测试为保护。

## 本地校验

`npm run check` 依次执行当前文档引用/npm 命令检查、归档完整性校验、API 资产与时间单位检查、Python/JavaScript 语法检查和 runner 单元测试。它不连接业务服务，也不能证明线上渠道、账号或 CI 当前可用。

历史交接与扫描快照不作为当前导航或命令校验对象；扫描快照改由 manifest 校验保留内容。普通文档链接会校验目标文件是否存在；Markdown 锚点、自然语言规则一致性和业务有效性仍需人工审查。
