# 架构与维护边界

## 执行依赖

`package.json` → `python-launcher.mjs` → `run-local.py` / `config/local-commands.json` → `scripts/run-*.py` → API runner / Playwright → 原始结果 → 报告渲染器。

CLI 文件保留原路径和命令；实现按公共能力与项目业务分层：

Telegram待确认列表由`qa_delivery/intake.py`负责现有需求目录匹配、子任务归并及明确批次选择，`preview_report.py`负责简洁显示。`preview.json`保存完整依据，`preview.md`是生成视图；本地preview使用只读SQLite连接，不初始化会恢复任务状态的Store。

| 位置 | 职责 | 依赖方向 |
| --- | --- | --- |
| `scripts/run-*.py`、原 API CLI | 参数和执行编排、兼容命令入口 | 调用公共能力与 FILBET 实现 |
| `scripts/qa_core/` | 环境、锁、跨平台进程、编解码、终端样式、通用报告 | 新公共模块不依赖 FILBET；旧 `contracts.py` 仅作兼容转发 |
| `scripts/qa_core/redaction.py`、`values.py` | 命令/错误脱敏、嵌套字段读取及存在性判断 | 纯函数，不读取配置或执行业务；调用者提供需隐藏的参数集合 |
| `scripts/filbet/` | API 请求实现、业务契约、认证/KYC/充值/流水/提现及 UI 资金支持 | 可依赖 qa_core，不动态加载业务 CLI |
| `tests/unit/` | 框架与业务实现的离线单元测试，包括开户工具回归 | `npm run test:unit` 统一发现；路径由 `support.py` 计算 |
| `ui/elements/`、`ui/framework/` | 页面操作及浏览器侧支持 | 维持当前 Playwright 组织方式 |

`filbet.controlled.ControlledFlow` 是受控业务的导入入口，每个实例持有独立的审批码、运行记录和报告状态。内部 operation 类按业务职责拆分，通过该对象协作，不单独作为 CLI。创建对象不加载凭据、不登录、不写业务数据；执行操作仍使用原环境变量和认证规则，因此不支持同一 Python 进程内并发运行多个资金流程。UI 资金支持直接创建该对象，不再动态加载受控 CLI。

`filbet/smoke.py` 保存原 API smoke 实现，`filbet/contracts.py` 保存 FILBET 路由/时间契约。`qa_core/process.py` 与 `qa_core/reporting.py` 收拢进程管理和通用报告组件；`filbet/reporting.py` 负责原资金文案和布局默认值。原 `ui_process.py`、`p0_report_template.py`、`ui_fund_flow.py`、`api_contracts.py` 及 `qa_core/contracts.py` 保留兼容导出；新代码使用规范模块路径。API 命令文件仍可按原路径执行。

Markdown基础表格由`qa_core.reporting.markdown_table`维护，原扫描/报表脚本保留`table`导入名。带换行清理等不同展示语义的渲染函数不强行合并。API、UI、full runner共享错误脱敏，但各自执行顺序、退出策略和敏感参数集合保持。

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
| 日期结论与维护记录 | 阶段说明、`docs/history/`；已删除原始结果须标明来源退出 |

上层导航链接到权威文件；代码与文档不一致时先确认实际行为，再修正语义，不能把过时文档当成强制执行脚本。

## 专项资产与兼容策略

旧扫描脚本、快照、截图与manifest已于2026-09-11按用户授权删除；[退出索引](../archive/interface-scans/README.md)保留原导航路径。当前接口资产在api/inventory、api/catalog与api/p0，构建器不依赖已删除扫描。`check:archive`保留CLI名称，现检查旧扫描目录只含退出说明。

当前执行包、最近真实需求批次和活动Telegram任务保持；旧结果目录中的临时脚本已迁移至固定模块后删除。具体范围见[整理记录](project-cleanup-2026-09-11.md)。

后续工作以 [新需求设计](../requirements/README.md) 为入口，按变更影响补用例并评估是否纳入 P0，不要求全接口自动化后再做需求测试。

受控 runner 已拆分至 `filbet/`；后续按实际需求扩展相应模块。公共核心仍在本仓库内维护，尚未发布为独立安装包；可通过白名单工具导出源码快照，能力清单、接入示例及验证边界见 [跨项目运行核心](runtime-reuse.md)。不直接复制业务目录。

## 本地校验

`npm run check` 依次执行当前文档引用/npm 命令检查、旧扫描退出检查、API 资产与时间单位检查、Python/JavaScript 语法检查和 runner 单元测试。它不连接业务服务，也不能证明线上渠道、账号或 CI 当前可用。

历史交接不作为当前导航或命令校验对象；旧扫描内容已删除，不再校验manifest。普通文档链接会校验目标文件是否存在；Markdown 锚点、自然语言规则一致性和业务有效性仍需人工审查。

## 新需求接口组合

`requirements/<编号>/api/cases.json`持有本需求参数与断言并引用验收Case；`scripts/run-requirement-api.py`负责CLI，`filbet/requirement_api.py`校验、编排和生成脱敏报告，复用`filbet/smoke.py`的认证/CBOR请求及公共本机锁。当前执行器只允许明确的查询路由；未知契约或需专用写入样本的闭环保留BLOCKED。报告按需求/运行时间隔离，P0入口与清理范围保持原定义。

## 提测消息编排

`run-telegram-qa.py`保留可执行兼容入口，参数与命令处理位于`qa_delivery/cli.py`；`qa_delivery/intake_ai.py`持久保存脱敏消息、调用AI识别意图并校验引用；`qa_delivery/intake.py`核对Story并绑定预览确认；`qa_delivery/batch.py`分别编排扫描、确认后执行及BUG提交的有限批次并退出；`qa_delivery/state.py`管理队列、outbox与确认快照，移除已退出生产流程的旧`/test`解析器；`pipeline.py`编排版本核对和AI缺陷分析，`requirement_bridge.py`绑定确认计划、统一API执行、冻结人工包及回填证据；未迁移需求复用旧查询执行器，新任务不启动专项UI浏览器，`connectors.py`管理Telegram/Jira投递。保留的独立浏览器工具只执行`telegram-ui.mjs`支持的动作，响应解码复用`ui/framework/business-response.mjs`，AI不直接调用Jira。状态与证据放在忽略的`reports/telegram/`，与P0结果隔离；该包不进入通用运行核心导出白名单。接入与恢复见[Telegram手册](telegram-qa.md)。

## 简洁用例与结果

新需求专项采用CSV用例、前置清单和四状态结果树，详见[用例与结果流程](testing-workflow.md)。历史结果已按用户授权清理；登录和数据准备不计业务PASS，脚本错误不直接计产品FAIL。

`scripts/qa_core/case_report.py`负责CSV校验、四状态归一化和结果树/CSV输出；`build-case-report.py`仅做离线CLI编排。新需求API报告自动调用公共输出；Telegram编排复用状态归一化，执行错误不进入产品FAIL候选。原证据JSON和报告路径保留。

## 新需求统一计划（ISOP-2027）

`run-requirement.py`负责选择、锁和产物；`qa_core/execution_plan.py`负责离线契约、参数集/变量、断言与旧查询视图，`qa_core/plan_runner.py`负责顺序步骤、四状态、依赖停止和检查点。`filbet/requirement_session.py`使用显式会话复用现有CBOR/TOTP，`requirement_adapter.py`绑定接口契约、写范围及本轮归属；`requirement_kyc.py`和`requirement_permissions.py`保存固定准备/对账/权限恢复方法。不从结果目录导入代码。

新请求不修改全局token；旧ControlledFlow仅在串行准备适配中临时加载并恢复环境。此适配尚不支持同进程并发准备，同账号并发不是本阶段能力。旧P0入口和清理范围保持。公共导出包含case_report/execution_plan/plan_runner，业务方法与凭据不导出。

阶段3 UI由`qa_core/ui_contract.py`校验固定资产，`filbet/requirement_ui.py`适配业务归属，`qa_core/json_worker.py`提供有界私有RPC，`requirement-ui-worker.mjs`驱动可导入的`ui/framework/requirement-ui.mjs`。浏览器会话按本轮actor隔离，认证token只在同actor的API/UI内存间同步。旧Telegram UI CLI薄封装`legacy-requirement-ui.mjs`，不改变旧发现流程。具体边界见[阶段3记录](new-requirement-stage3.md)。

团队交付由`qa_core/team_delivery.py`生成冻结执行包、校验人工CSV并汇总明确自动来源；`prepare-test-delivery.py`仅作离线CLI。执行方式保存在plan.delivery中，原层级/编号不变；报告仅在团队模式附加执行方式及来源列，旧CSV协议兼容。见[团队流程](team-testing.md)。

新统一执行和团队交付默认仅生成results.csv/results.html；`--extra-views`按需生成其他视图。公共write_views保留旧默认值以兼容P0外的旧查询/通用报告消费者；原始结果及快照不因视图精简而删除。

业务总表和API数据视图由`qa_core/case_catalogue.py`生成，`export-requirement-cases.py`仅负责选择需求和加载已验证JSON。总表读取test-cases.md的固定业务表；执行历史表不参与导出。API组合逐条验证总用例引用，缺失/错误引用时拒绝更新视图；不会聚合成验收PASS。CSV由现有公共csv_text输出，保持UTF-8 BOM和公式注入防护，不新增表格运行依赖。
