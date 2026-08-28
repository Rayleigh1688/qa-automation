# AI 对话交接

这是新 AI 或新对话进入本仓库的第一份文档。修改测试资产前先阅读本文件，再按下方目录职责进入对应子项目。

## 项目目标

建设可维护的 FILBET 自动化回归基线。当前只聚焦 P0 主流程：

1. 注册登录。
2. KYC 状态和必要前置。
3. 充值。
4. 投注。
5. 派彩结果，以及投注/账变核对。
6. 提现。
7. 管理后台相关记录、列表、报表和审核。

P0 稳定前不扩展 P1/P2。API 和 UI 分别证明同一主流程的不同部分，不能相互替代。

## 新对话阅读顺序

1. 本文件：当前方向、约束、阻塞和下一步。
2. `README.md`：全局规则、命令、CI 和目录边界。
3. `testing-plan/00-测试自动化总体规划.md`：路线图和优先级边界。
4. 再读本次工作涉及子项目的 README 或 runbook。
5. 执行 `git status --short`，只检查和本次工作相关的文件。工作区可能包含用户改动，除非明确要求，不得回退。

## 文档地图

| 位置 | 职责 | 何时阅读 |
| --- | --- | --- |
| `README.md` | 项目总说明书：全局规则、命令、CI、结果边界和高层状态。 | 每次。 |
| `AI-HANDOFF.md` | 跨对话入口：当前进度、阻塞、阅读顺序和下一阶段工作。 | 每次新对话。 |
| `testing-plan/` | 自动化路线图。`00-` 为总体规划，`01-07` 分别定义 P0/P1/P2、CI、AI、性能和可观测性阶段。 | 调整范围、优先级、验收标准或阶段顺序时。 |
| `api/p0/README.md` | P0 API 资产模型、执行语义、接口替代关系和测试账号分层。 | 修改 P0 API 资产或命令时。 |
| `api/p0/*.csv` | 固定 API 资产：候选接口池、主流程场景矩阵、可执行用例索引。 | 新增或调整 P0 API 覆盖时。 |
| `api/inventory/` | 从接口文档整理出的全量接口资产。 | 发现或核对接口路径时。 |
| `api/runbooks/API.md` | API 执行、鉴权、环境变量和受控写操作手册。 | 执行或调试 API 测试时。 |
| `api/runbooks/ADMIN.md` | 后台登录和审核操作说明。 | 使用后台 API 或审核动作时。 |
| `ui/README.md` | UI 范围、Playwright 结构、固定视口、命令和输出边界。 | 所有 UI 自动化工作。 |
| `ui/cases/`、`ui/elements/`、`ui/framework/`、`ui/data/` | UI 用例、页面/操作封装、共享能力和配置数据。 | 实现 UI 覆盖时。 |
| `harness/` | 已知缺陷、波动、API/UI 调试记录和只读数据库字段笔记。 | 测试失败或环境行为不清楚时。 |
| `skills/` | API、UI 和业务规则的长期操作准则。 | 引入新的测试方式前。 |
| `scripts/` | runner、报告渲染、清理和接口资产维护脚本。 | 修改执行或报告行为时。 |
| `api/results/`、`ui/results/`、`ui/reports/` | 最近一次生成物，只作执行证据，不作为长期手册。 | 查看最近执行结果时。 |

## 不可违反的规则

- 确认的规则、结论或执行策略必须在同一改动中同步到对应 Markdown 或 CSV，不能只留在对话里。
- API 结果只写入 `api/results/`；UI 原始结果写入 `ui/results/`，UI 可读报告写入 `ui/reports/`。
- 结果目录使用固定文件名，只保留最近一次执行；历史由 CI 归档。
- 密码、OTP、TOTP seed、token、cookie、会话和原始个人信息只放本地忽略配置或 CI 凭据，不写入 Markdown、CSV、报告或 Git。
- 测试环境可通过批准的 API 造数；数据库只读用于诊断，不能直接改库。
- 现有工作区改动默认属于用户，未经明确要求不得清除或回退。

## 当前 P0 API 状态

完整 P0 执行入口：

```bash
python3 scripts/run-api-tests.py p0
```

它会执行只读正例、默认安全反例和受控写主流程：注册、充值下单、后台补单、提现申请、后台审核同意和成功标记。提现以后台成功记录为验收，不验证项目外的实际到账。

只读/反例快速检查：

```bash
python3 scripts/run-api-tests.py p0 --safe-only
```

当前基线：

- P0 只读 smoke 为 30 条：客户端 25 条、后台 5 条。
- 默认安全反例为 14 条。
- 受控主流程支持分离只读、充值写入和提现测试账号。
- FAT 后台登录使用固定登录码；审核动作使用本地审批密钥生成的真实 TOTP。
- 每次 P0 执行生成 Markdown 和离线 HTML 主流程报告：`api/results/p0-main-flow-report.md`、`api/results/p0-api-report.html`。

当前环境和覆盖边界：

- 曾使用的客户端手机号因高频短信请求被 FAT 限制。登录拿不到 token 后的 `token` 连锁失败属于账号/环境前置问题，不能直接视为下游 API 回归。
- 账号需要分层：`CLIENT_PHONE` 用于只读检查，`WRITE_CLIENT_PHONE` 用于充值和受控写，`WITHDRAW_CLIENT_PHONE` 必须是已 KYC、已绑定提款账户、可提现且无流水限制的专用账号。
- FAT 当前未校验充值通道上下限，属于已确认后端缺陷。会创建订单的限额契约探针不进入默认 CI，修复后再显式复验。
- 投注和派彩尚未形成完整 API-only 闭环。API 当前验证游戏入口、列表和历史记录；真实第三方投注交互是下一阶段 UI 探索重点。

## 下一阶段：UI 网络发现

目标是通过客户端真实操作发现 P0 流程接口，再将已确认接口纳入 API P0 资产和 runner。

首选方案是**窗口化 Playwright + 网络捕获**，不以单独手工浏览器作为主要方案。Playwright 可在固定 `1366x768` 可视窗口中捕获同一 browser context 内页面、iframe、弹窗和新标签页的请求/响应，也可以保留 HAR/trace 作为本地证据。

实施顺序：

1. 增加独立的 UI 网络捕获能力，将脱敏请求/响应摘要和 HAR/trace 写入已忽略的 `ui/results/`。
2. 使用持久化 Playwright 登录态，依次走登录、KYC 入口/状态、充值、提现入口、游戏启动、投注和派彩展示。
3. 三方游戏 iframe/canvas 保持固定 `1366x768` 视口，并将相对坐标保存在 `ui/data/client-game-actions.json`。
4. 从捕获结果确认真实路径、参数、响应字段和版本替代关系。
5. 将已确认请求补入 `api/p0/interface-shortlist.csv`、`api/p0/test-cases.csv`、`api/p0/main-flow-scenarios.csv`，确认契约后再改 API runner。
6. 原始抓包只保留本地；长期文档只记录脱敏后的接口契约和结论。

窗口化浏览器适合探索、二维码/验证码人工协助和第三方游戏行为；抓取 HTTP 流量本身依靠 Playwright 网络事件，不依赖手工 DevTools。普通 Playwright 事件无法充分观察二进制、加密、service worker 等情况时，才以 DevTools 作为补充。

## 当前未提交工作快照

上次交接时，以下文件存在与 P0 执行和报告相关的未提交修改：

- `Jenkinsfile`
- `README.md`
- `api/p0/README.md`
- `api/runbooks/API.md`
- `scripts/render-main-flow-report.py`
- `scripts/run-api-tests.py`

该清单只是快照，开始工作前仍必须以 `git status --short` 为准。

## 对话结束检查

1. 将确认的规则同步到对应 README、计划、runbook、CSV 或 harness 记录。
2. 说明执行了什么、未执行什么，以及阻塞属于产品、环境、测试数据还是测试代码。
3. 不提交密钥或生成报告。
4. 当方向变化时，更新本文件的“当前 P0 API 状态”和“下一阶段”。
