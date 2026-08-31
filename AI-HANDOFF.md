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

- P0 safe smoke 为 39 条：客户端 34 条、后台 5 条；最近一次按真实 FAT 环境执行通过 39/39。
- 默认安全反例为 14 条。
- 受控主流程支持分离只读、充值写入和提现测试账号。
- FAT 后台登录使用固定登录码；审核动作使用本地审批密钥生成的真实 TOTP。
- 每次 P0 执行生成 Markdown 和离线 HTML 主流程报告：`api/results/p0-main-flow-report.md`、`api/results/p0-api-report.html`。

当前环境和覆盖边界：

- 曾使用的客户端手机号因高频短信请求被 FAT 限制。登录拿不到 token 后的 `token` 连锁失败属于账号/环境前置问题，不能直接视为下游 API 回归。
- 账号需要分层：`CLIENT_PHONE` 用于只读检查，`WRITE_CLIENT_PHONE` 用于充值和受控写，`WITHDRAW_CLIENT_PHONE` 必须是已 KYC、已绑定提款账户、可提现且无流水限制的专用账号。
- FAT 当前未校验充值通道上下限，属于已确认后端缺陷。会创建订单的限额契约探针不进入默认 CI，修复后再显式复验。
- 客户端真实接口已完成一轮反向修复：充值渠道改为 `/finance/channel/list?mode=1`，充值记录去除旧 `status` 筛选，投注记录改为客户端实际的 `time_flag=0` 查询；KYC 奖励、登录后弹窗、盲盒、投注旋转活动、充值活动、Filcoin、VIP 规则和购买免费旋转配置已进入 `api/p0/test-cases.csv`。
- 投注和派彩尚未形成完整 API-only 闭环。API 当前验证游戏入口、列表和历史记录；真实第三方投注交互由 Pixel 7 固定视口 UI 链路补充。

## 下一阶段：管理后台 P0 梳理

目标是基于客户端主流程和已通过的 P0 safe smoke，补齐管理后台 P0 查询、审核、报表、权限和数据核对接口，形成“前台动作 + 后台记录 + 前台状态刷新”的闭环。

当前收口判断：客户端接口和主要功能已基本跑通，并已用 UI Network 反向修复 `api/p0/` 资产；下一轮优先梳理管理后台 P0 查询、审核、报表和权限接口。后台部分完成并连续稳定执行后，P0 阶段即可进入验收收尾。

首选方案是**窗口化 Playwright + 网络捕获**，不以单独手工浏览器作为主要方案。客户端页面和三方游戏页都固定使用 Pixel 7 手机浏览器格式 `412x915`；三方游戏 iframe/canvas 点击使用该固定视口下的相对坐标。Playwright 可捕获同一 browser context 内页面、iframe、弹窗和新标签页的请求/响应，也可以保留 HAR/trace 作为本地证据。

已新增独立发现入口：

```bash
npm run test:ui:network-discovery
```

该命令按 Pixel 7 手机格式登录客户端后探索首页、Game、Rewards、Filcoin、My、钱包、充值、提现、KYC、银行卡和记录入口，输出 `ui/results/client-network-discovery.json`、`ui/results/client-network-discovery.har`、`ui/results/client-network-discovery-trace.zip` 和 `ui/reports/client-network-discovery-report.md`。输出已做脱敏，只用于发现和人工确认，不进入默认 CI 门禁。

客户端登录/进首页顺序：

1. 首次进入固定手机格式客户端，勾选责任协议并点击继续。
2. 点击首页 `Register / Login`。
3. 若常规浏览器出现已记住账号，测试其他账号时点击 `Other Accounts`。
4. 新账号注册或登录优先走 `SMS OTP`；测试环境 OTP 固定为 `111111`。
5. 登录后先关闭 `Notice` 提示弹窗。
6. 关闭客户端活动弹窗；该弹窗可能出现两次，自动化需要循环判断。
7. 关闭底部下载 APP 提示；若右下角活动浮窗遮挡关闭按钮，先关闭或移开浮窗。
8. 完整首页出现余额、底部导航和主内容后，再继续探索 P0 入口。

测试环境页面加载最多等待 5 秒；超过 5 秒不直接失败，记录为加载过慢 warning，除非该步骤是登录成功、关键入口存在等硬前置。

My 页资金和记录入口：

- `Withdraw` 是提现入口。
- `Deposit` 是充值入口。
- `Transaction` 可查看充值、提现和账变记录。
- `Bet History` 是投注记录入口。
- 这些入口可以在测试环境内直接点击探索；不创建订单、不提交资金动作时只记录 Network 和页面状态。

KYC 是 P0 主流程，采用 UI + API 双验证：

- UI 负责证明真实页面流程：新账号首页默认弹出 KYC 引导，点击 `Verify Now` 后二次确认进入 KYC；FAT 未开启 eKYC 时，ID 类型和图片内容可使用测试素材；依次完成证件/图片、地址、个人信息、核对提交，最终出现 `KYC successful` 和 `Return to Homepage`。
- API 负责证明业务状态：提交前后 `/member/kyc/detail` 等前台状态变化、后台待审记录出现、审核通过/驳回后前台状态刷新，以及充值/提现/投注权限受 KYC 状态影响的规则。
- UI 不替代后台审核断言；API 不替代真实前端上传、表单校验和提交路径。

测试账号池：

- KYC 新账号使用菲律宾 `09` 号段测试池，格式 `090XXXXXXXX`，首个账号从 `09000000001` 开始。
- 测试环境登录/注册 OTP 固定为 `111111`。
- KYC 可使用新账号，也可使用已驳回/未通过 KYC 的账号重复提交，避免账号池用尽。
- `9888888050` 已知存在提现流水限制；提现正例需换无流水限制账号，或先通过后台解除该账号流水限制。
- 充值页 `Multiple Deposit Bonus` 活动开关默认不参加；参加活动会产生提现流水限制。若要验证无流水限制提现，应保持该开关关闭/置灰。

客户端 Network 发现和 API 反向修复结果：

1. `npm run test:ui:network-discovery` 负责脱敏捕获客户端真实接口，只用于发现和人工确认，不进入默认 CI。
2. `api/p0/test-cases.csv` 已从 30 条扩展到 39 条，并通过真实 FAT API smoke 39/39。
3. `api/p0/interface-shortlist.csv` 已标记前端真实使用的支撑接口；首页素材、FB 活动、首页分区等暂列 `token_required` 候选，未全部升格为门禁。
4. 原始抓包只保留本地；长期文档只记录脱敏后的接口契约和结论。
5. 下一轮回到管理后台梳理 P0：当前用户、权限、KYC 待审/审核、充值补单、提现审核、报表、资金和记录查询。

窗口化浏览器适合探索、二维码/验证码人工协助和第三方游戏行为；抓取 HTTP 流量本身依靠 Playwright 网络事件，不依赖手工 DevTools。普通 Playwright 事件无法充分观察二进制、加密、service worker 等情况时，才以 DevTools 作为补充。

业务同学熟悉页面路径时，若自动化未能打开充值、提现、KYC、银行卡或记录入口，可直接指出真实入口文案、页面路径或固定视口下可点击区域，再沉淀到 `ui/data/`。

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
