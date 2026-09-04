# QA Automation

这是一个用于逐步建设测试自动化体系的工作区。

## 新对话 / 新 AI 入口

开始新的对话或交接给另一位 AI 时，先阅读 [AI-HANDOFF.md](AI-HANDOFF.md)。它记录当前进度、阻塞、文档阅读顺序、敏感信息边界，以及下一阶段的具体工作；本文件继续作为项目总说明书。

Codex 会自动发现仓库级 [`filbet-p0-automation` Skill](.agents/skills/filbet-p0-automation/SKILL.md)。它只负责根据任务加载必要资料，不复制实时状态。

AI 文档按“由浅入深”进入：

1. [AI-HANDOFF.md](AI-HANDOFF.md)：一分钟了解当前结论、证据、例外和下一步。
2. 本文件：全局边界、目录、统一命令和 CI 规则。
3. [skills/README.md](skills/README.md)：按 API、UI 或业务规则选择长期方法。
4. 子项目说明：[`api/p0/README.md`](api/p0/README.md)、[`ui/README.md`](ui/README.md) 和 `api/runbooks/`。
   FAT/UAT 差异统一查看 [`api/runbooks/ENVIRONMENTS.md`](api/runbooks/ENVIRONMENTS.md)。
5. [harness/README.md](harness/README.md)：只有失败、环境差异或数据状态不清楚时再进入排障资料。
6. `api/results/`、`ui/results/`、`ui/reports/`：最后查看最近一次证据，不把生成报告当作规则来源。

## 目录结构

```text
testing-plan/    测试自动化建设规划
skills/          测试方法、规范、业务规则沉淀
harness/         调试经验、已知问题、失败分析沉淀
api/             API 自动化测试资产
  inventory/     接口文档扫描清单
  catalog/       按调用端和后台业务模块自动生成的接口检索视图
  p0/            P0 场景、用例等固定资产
  results/       API 最近一次执行结果和报告，已忽略
  runbooks/      API 执行和调试入口文档
ui/              UI 自动化测试
  cases/         Playwright 用例
  elements/      页面对象和操作封装
  framework/     UI 测试基础能力，如环境读取、Network 记录
  data/          UI 测试数据
  reports/       UI 最近一次可读报告
  results/       UI 最近一次原始执行结果，已忽略
performance/     性能测试
interface-discovery/ FAT 客户端与管理后台当前接口发现、映射和分类计划
client-button-map/  客户端页面与控件参考清单
fat-client-interface-scan/ FAT 客户端接口发现独立资产
fat-admin-interface-scan/ FAT 管理后台接口发现独立资产
pagcor-admin-interface-scan/ FAT 合规管理后台接口发现独立资产
agency-admin-interface-scan/ FAT 代理管理后台接口发现独立资产
agency-portal-interface-scan/ FAT 代理前台接口发现独立资产
tools/           脱离门禁主流程的测试数据准备工具；写操作必须显式执行
scripts/         辅助脚本
```

## 当前状态

当前阶段：P0 核心自动化已形成可执行基线；接口发现暂停，第一优先级转为让 FAT/UAT P0 完全由确定性代码单命令执行，不依赖 AI 临场操作或判断

阶段成果见 [`FILBET-QA阶段成果报告-2026-09-04.md`](FILBET-QA阶段成果报告-2026-09-04.md)。

另有独立的 FAT 当前接口发现专项，通过真实 UI 收集“页面 → 操作 → 接口”证据并与 inventory/catalog 分类映射；该专项现已冻结为阶段快照，不改变现有 P0/P1 范围。执行状态见 [`interface-discovery/README.md`](interface-discovery/README.md)。

- P0 资产已重排为 8 条端到端主流程和 57 条整体用例：31 条 safe smoke（客户端 18、后台 13）、15 条 API 登记反例（默认执行 13 条）、10 条受控写/UI 协作项和 1 条已实现状态 UI 反例。
- `test-cases.csv` 已成为正反例统一索引，并按真实业务依赖排序；接口文档扫描清单只用于发现，不再决定 P0 范围或访问顺序。
- P0 资金写操作按阶段执行：API 充值与后台补单后必须停在检查点，UI 完成真实投注，API/数据库确认投注和流水，再由 API 提现；后台审核仍只处理本次创建的订单。
- 客户端 UI 自动化：登录注册、充值、提现入口、Transaction、Bet History 和游戏链路已跑通 Network 发现；发现到的主要客户端接口已同步到 `api/p0/`。KYC 保留最小 P0 闭环，扩展证件组合、OCR/eKYC、驳回重提矩阵归 P1。
- 管理后台 API：已把“用户与权限、KYC 最小审核闭环、充值补单、提现审核、财务报表、资金记录与核对”纳入 P0。补单、提现同意/成功仍只处理本次 controlled flow 创建的订单。
- UI 定位策略：对难以稳定抓取的三方游戏/canvas 场景，采用固定视口下的 Playwright + 坐标定位组合策略。
- 当前主要风险：客户端自动化账号可能因频繁请求短信被 FAT 限制；CI 需要使用稳定的专用客户端账号或预置 token 策略。充值通道限额后端校验在 FAT 存在已知缺陷，越界契约探针不默认进入 CI。管理后台审核类动作使用已配置的真实 Google Authenticator 动态令牌；后台登录在 FAT 使用固定 `ADMIN_GOOGLE_CODE=111111`。
- 2026-08-31 P0 快速门禁连续 3 轮稳定：每轮 FAT safe smoke 31/31、默认反例 13/13；UI 前两轮仅保留已确认条款缺陷，第三轮 11/11。完整受控链路已完成 KYC 审批与前台刷新、充值 1200、固定单注 1000 的流水驱动投注、提现 1000 和前后台订单关联核对；统一核对结果 PASS。
- 2026-09-02 UAT 的 8 条 P0 主流程和统一资金链核对已 PASS：Maya 充值 1200、BNG `Coins` 单注 100 完成 6 次投注、流水归零、Maya 提现 500 进入后台 `under_review`。默认 UI 为 10/11，唯一失败是已明确接受本轮例外但尚未修复的“未勾选登录条款仍可登录”；实时证据以 [`AI-HANDOFF.md`](AI-HANDOFF.md) 为准。

## 执行规则

- 每次确认规则性问题，都要同步修改对应文档或数据文件，避免只留在对话上下文里。
- 影响测试范围、优先级或执行策略的规则，优先写入 `testing-plan/` 和 `README.md`。
- 影响 P0 接口用例的规则，必须同步更新 `api/p0/main-flow-scenarios.csv`；说明性规则统一写入 `api/p0/README.md`。
- 影响执行方法、账号、令牌、环境变量或调试步骤的规则，写入 `api/runbooks/` 或 `harness/`。
- API 和 UI 自动化结果必须分开：API 结果只写入 `api/results/`；UI 原始结果、截图、trace、视频只写入 `ui/results/`，UI 可读报告写入 `ui/reports/`。
- 测试结果目录只保留最近一次执行产物。每次执行前可以清空旧产物；runner 和报告生成脚本必须使用固定文件名覆盖写入，不做增量追加，不长期保留历史报告。

## AI 参考手册分工

- `README.md`：项目总说明书，记录当前阶段、最高优先级、统一命令、CI 门禁和全局规则。
- `AI-HANDOFF.md`：新对话和新 AI 的交接入口，记录当前进度、环境阻塞、接力顺序和下一阶段工作；方向变化时必须同步更新。
- `testing-plan/`：测试自动化路线图，记录阶段目标、优先级定义、建设边界和验收标准。
- `api/p0/README.md`：P0 API 固定资产说明，解释 shortlist、main-flow、test-cases 的关系。
- `api/runbooks/`：API 执行手册，记录客户端/后台登录、鉴权、环境变量、受控写操作和调试命令。
- `ui/README.md`：UI 自动化小项目说明，记录 Playwright 目录、执行命令、结果目录和定位策略。
- `harness/`：从 [`harness/README.md`](harness/README.md) 进入；记录失败归因、flaky、环境限制、历史坑位，数据库只读字段观察记录在 `harness/database-debug.md`。
- `skills/`：从 [`skills/README.md`](skills/README.md) 进入；保存 API/UI 测试方法和业务规则。正式可发现的项目 Skill 位于 `.agents/skills/`。
- `api/results/`、`ui/results/`、`ui/reports/`、`playwright-report/`、`test-results/`：仅保存最近一次执行产物，不作为参考手册。

接口新旧版本交替时，版本替代关系维护在 `api/p0/README.md`；具体失败响应和环境现象维护在 `harness/known-errors.md`。

## P0 主流程优先级

当前第一优先级只围绕主流程建设：

1. 登录注册。
2. KYC 最小闭环：提交、后台审核、前台状态刷新。
3. 充值。
4. 投注。
5. 投注/派彩记录。
6. 钱包、账变及前后台数据核对。
7. 提现及流水限制反例。
8. 后台权限、报表与主流程总核对。

后台 P0 阶段内部顺序为：当前用户/权限 → KYC 本次提交审核 → 充值待审/补单 → 提现待审/审核 → 财务报表 → 资金记录及前后台订单级核对。

其它功能等这些主流程相关能力稳定通过后再继续扩展。

KYC 最小 P0 采用 UI 和 API 双重验证：提交成功、后台审核和前台状态刷新进入 P0；驳回重提、OCR/eKYC、证件及字段组合等扩展矩阵归 P1。

客户端接口版本以 `npm run test:ui:network-discovery` 的真实请求为准。P0 使用新版充值渠道、充值记录、游戏列表和投注记录路径；活动、弹窗、盲盒、Filcoin、VIP、代理和收藏等非核心接口保留在候选池，不进入 P0 门禁。

## P0 自动化执行

统一 API 等级执行：

```bash
python3 scripts/run-api-tests.py p0
```

一次执行多个等级：

```bash
python3 scripts/run-api-tests.py p0 p1
```

P0 只读快速检查：

```bash
python3 scripts/run-api-tests.py p0 --env .env.fat --scope FAT --safe-only
python3 scripts/run-api-tests.py p0 --env .env.uat --scope UAT --safe-only
```

P0 API 独立组合（包含 safe、negative，以及除三方真实投注外的新账号注册、KYC、充值、流水处理、Maya 绑定和提现 API 流程）：

```bash
npm run test:p0:api
ENV_FILE=.env.uat npm run test:p0:api
```

只组合 API 查询和保护性反例时使用 `npm run test:p0:api:read`。写操作在 FAT/UAT 属于正常 P0 场景，不是全局禁止项；是否创建订单由所选命令/场景明确表达。

需要逐个验证可由 API 完成的 P0 业务能力时，使用独立操作入口：

```bash
ENV_FILE=.env.fat npm run test:p0:api:register
ENV_FILE=.env.fat npm run test:p0:api:kyc-submit
KYC_CLIENT_UID=<uid> ENV_FILE=.env.fat npm run test:p0:api:kyc-approve
ENV_FILE=.env.fat npm run test:p0:api:deposit-create
P0_DEPOSIT_ID=<deposit-id> ENV_FILE=.env.fat npm run test:p0:api:deposit-check-client
P0_DEPOSIT_ID=<deposit-id> ENV_FILE=.env.fat npm run test:p0:api:deposit-check-admin
P0_DEPOSIT_ID=<deposit-id> ENV_FILE=.env.fat npm run test:p0:api:deposit-approve
ENV_FILE=.env.fat npm run test:p0:api:withdraw-create
P0_WITHDRAW_ID=<withdraw-id> ENV_FILE=.env.fat npm run test:p0:api:withdraw-check-client
P0_WITHDRAW_ID=<withdraw-id> ENV_FILE=.env.fat npm run test:p0:api:withdraw-check-admin
P0_WITHDRAW_ID=<withdraw-id> ENV_FILE=.env.fat npm run test:p0:api:withdraw-approve
```

每条命令是一次全新运行：客户端操作重新取得 client token，后台操作重新取得 admin token；token 不跨命令传递。创建操作把业务 ID 写入 `api/results/operations/<operation>.json`，后续查询或审核通过显式业务 ID 精确关联，不会回退处理列表第一条记录。每条命令无论通过或业务失败都会生成同路径的 HTML 报告。真实三方投注以及依赖本轮投注的派彩/流水归零仍由 UI/完整主流程负责，不伪装成纯 API 独立操作。

注册命令未显式配置 `REGISTER_PHONE` 时，会先后台登录并验证会员手机号精确筛选，再从 `9000000001` 开始递增查找首个不存在的账号。FAT/UAT 游标分别保存在 Git 忽略的 `api/local-state/register-phone-<environment>.json`；游标保存本次找到的号码，下次从该号码复查，已注册才继续加一，因此中断不会无故跳号。

API-only 资金调试可执行 `npm run test:p0:api:deposit-clear-turnover`：同一次 npm 运行只登录一次客户端和后台，完成充值、补单、查询剩余流水；剩余流水非零时调用后台清空并复查为 0，已经为 0 时不重复写入。该路径明确属于测试环境管理动作，不代表真实投注完成。新账号提现前还必须设置钱包密码并绑定提款账户；提现正例最低金额固定为 100。

UI P0：

```bash
npm run test:ui:p0
ENV_FILE=.env.uat npm run test:ui:p0
```

API + UI P0：

```bash
npm run test:p0
```

完整受控 P0 验收（会执行 KYC 状态闭环、充值补单、真实投注、流水轮询、提现提交和前后台关联核对）：

```bash
npm run test:p0:full
```

说明：

- `npm run test:p0` 是可重复快速门禁：API safe/negative + 默认 UI，不创建新的充值、投注或提现记录，并保留最近一次完整资金链证据。
- 每次 API runner 或 UI 命令启动都重新登录并取得新 token；token 只在本次 runner/Playwright suite 内共享，KYC、充值、投注、提现由独立操作组合成场景，不跨命令复用历史 session/storage state。
- `npm run test:p0:full` 是显式受控写入口，严格按永久未 KYC 账号提现拦截 → 独立 KYC 账号闭环 → 充值 → UI 投注 → 流水核对 → API 提现建单 → 后台按订单 ID 关联执行；任一阶段业务失败立即停止。
- `test:p0:full` 在任何业务动作前统一执行 preflight，校验环境 URL/scope、账号 lane 隔离、动态 OTP/TOTP 来源、金额、KYC 图片、Python/npm/Playwright 依赖；未显式传 `--scope` 时按 `.env.fat` / `.env.uat` 文件名推断 FAT/UAT。
- `python3 scripts/run-api-tests.py p0` 是 API 子流程入口，执行 safe/negative 并将资金链推进到充值与补单检查点；不会跳过真实投注直接提现。
- 只复验后台 safe smoke 时，可执行：`python3 scripts/api-smoke-runner.py --cases api/p0/test-cases.csv --with-admin-login --base admin --execute --insecure --body-format cbor --out /tmp/admin-p0-smoke.json`。
- `python3 scripts/run-api-tests.py p0 p1` 按等级依次执行；当前 P1 资产不存在时会跳过并提示。
- `--safe-only` 跳过注册、充值、提现和审核等受控写操作，只执行只读/反例检查。`--include-write` 保留为旧命令兼容参数；P0 默认包含受控写的充值检查点。提现以后台成功记录为验收，不校验项目外收款账户或真实到账，只应在测试环境或专用 UAT 测试数据下执行。
- `test:ui:p0` 默认不执行真实投注。需要点击三方游戏内投注区域时，必须显式设置 `EXECUTE_BET=true`。
- API 和 UI P0 分别执行、分别判定。Maya UI 提现使用 `npm run test:ui:withdraw-contract` 独立验证客户端建单；未 KYC 提现前置使用 `npm run test:ui:unverified-withdraw`。两者不会替代 API 提现契约。
- 正向资金链单注由 `CLIENT_GAME_BET_AMOUNT` 控制：FAT/UAT 当前统一为 100，UAT 上限仍为 100；`scripts/run-turnover-bet.py` 按所选环境的剩余流水动态计算次数。投注后再次核对流水，归零才进入提现。完整差异见 [`ENVIRONMENTS.md`](api/runbooks/ENVIRONMENTS.md)。
- 后台登录固定码和审核动态码是两套东西：`ADMIN_GOOGLE_CODE=111111` 只用于 FAT 后台登录，审核/补单/KYC 审批使用 `ADMIN_APPROVAL_TOTP_SECRET` 生成真实动态码。
- API 执行会覆盖 `api/results/` 下同名结果和报告；UI 执行会覆盖 `ui/results/` 和 `ui/reports/` 下同名产物。需要历史记录时，以 CI 归档为准，不在仓库工作区内累积。
- 三类 P0 HTML 报告使用同一模板但保持独立判定口径：`api/results/p0-api-report.html` 展示本次 API 请求/断言，`ui/reports/p0-ui-report.html` 展示本次 Playwright 用例，`api/results/p0-main-flow-report.html` 只在 API+UI 组合验收中按 8 条端到端主流程汇总。三个入口结束时分别打印对应的 `file://` 绝对地址。
- 需要单独清空生成物时，执行 `python3 scripts/clean-test-artifacts.py all`；只清 API 或 UI 时分别用 `api`、`ui` 参数。
- FAT 主流程使用同一普通会员完成不参加活动的充值、投注和提现；充值参数固定 `cashback_flag=0&rotation_flag=0` 且不传活动 `product_id`。自动选择充值通道时，本次金额必须符合通道 `min_amount/max_amount`；`amount_limit` 只作为快捷金额优先项。普通存款基础流水在提现前正常完成，但不在主链路中测试流水限制拒绝。
- 充值页 `Multiple Deposit Bonus` 活动开关默认不参加；参加活动会产生提现流水限制。`9888888050` 已知存在提现流水限制，提现正例需换无流水限制账号或先后台解除限制。
- KYC 新账号池使用 `090XXXXXXXX`，首个账号从 `09000000001` 开始；测试环境 OTP 固定为 `111111`，已驳回/未通过 KYC 的账号可再次提交。
- 本地或 CI 通过 `WRITE_CLIENT_PHONE`、`WRITE_CLIENT_PASSWORD` 注入 `fund_flow_account`；兼容变量 `BET_CLIENT_PHONE` 和 `WITHDRAW_CLIENT_PHONE` 可指向同一账号。OTP 变量只保留给注册、首次设密和显式 OTP 专项。未 KYC 提现反例固定使用永久不提交 KYC 的 `PRE_KYC_CLIENT_PHONE`；最低提现金额走成熟账号 API 反例，不准备低余额账号。`RESTRICTED_CLIENT_PHONE` 仅预留给 P1 活动流水专项。

## CI 门禁

Jenkinsfile 已支持参数化执行：

| 参数 | 推荐值 | 用途 |
| --- | --- | --- |
| `TARGET_ENV` | `fat` / `uat` | `fat` 用于发布 UAT 前测试环境验证，`uat` 用于发布 UAT 后验证 |
| `P0_SCOPE` | `api_all` | 执行 API 只读正例和默认安全反例；不创建测试订单 |
| `EXECUTE_BET` | `false` | 默认不做真实投注点击 |

推荐发布流程：

1. 发布 UAT 前，在测试环境执行：`TARGET_ENV=fat`、`P0_SCOPE=api_all`。
2. 发布 UAT 后，在 UAT 执行：`TARGET_ENV=uat`、`P0_SCOPE=api_all`。
3. UI 自动化作为补充检查，需要同时验证安全 API 检查与前端时执行 `P0_SCOPE=api_and_ui`；只执行 UI 时使用 `ui_only`。
4. 涉及注册、充值、提现和审核链路验证时，人工触发 `P0_SCOPE=api_write`。该 scope 执行完整受控主流程，必须确认测试账号、活动流水、审核令牌和资金影响可控。

CI 需要通过 Jenkins 环境变量或凭据注入：

```bash
FAT_API_URL=https://client-fat.filbet2025.com
FAT_ADMIN_URL=https://admin-fat.filbet2025.com
FAT_CLIENT_BASE_URL=https://client-fat.filbet2025.com
UAT_API_URL=<uat client api url>
UAT_ADMIN_URL=<uat admin url>
UAT_CLIENT_BASE_URL=<uat client url>
CLIENT_PHONE=<client phone>
CLIENT_PASSWORD=<client password>
CLIENT_AUTH_MODE=password
CLIENT_OTP=<otp>
REGISTER_PHONE=<allocated 090XXXXXXXX KYC test phone>
REGISTER_PASSWORD=<new-account password>
REGISTER_OTP=<otp>
WRITE_CLIENT_PHONE=<controlled write/deposit client phone>
WRITE_CLIENT_PASSWORD=<controlled write/deposit client password>
WRITE_CLIENT_OTP=<otp>
BET_CLIENT_PHONE=<controlled bet/payout client phone>
BET_CLIENT_OTP=<otp>
WITHDRAW_CLIENT_PHONE=<dedicated withdraw client phone>
WITHDRAW_CLIENT_OTP=<otp>
CLIENT_WALLET_PASSWORD=<numeric wallet password for Maya UI withdrawal>
PRE_KYC_CLIENT_PHONE=<permanent BASIC account; never submit KYC>
PRE_KYC_CLIENT_PASSWORD=<local password>
PRE_KYC_CLIENT_OTP=<fat otp>
RESTRICTED_CLIENT_PHONE=<active turnover-restricted client phone>
RESTRICTED_CLIENT_OTP=<otp>
ADMIN_EMAIL=<admin email>
ADMIN_PASSWORD=<admin password>
ADMIN_DEVICE_ID=<x-device-id>
ADMIN_GOOGLE_CODE=111111
ADMIN_APPROVAL_TOTP_SECRET=<approval totp secret>
ADMIN_APPROVAL_TOTP_ALGORITHM=SHA256
```

CI 归档产物：

- `api/p0/README.md`
- `api/results/*.md`
- `api/results/*.json`
- `api/results/*.html`
- `ui/reports/*.md`
- `ui/results/**/*.json`
- `ui/results/screenshots/**/*`
- `playwright-report/**/*`
- `test-results/**/*`

## UI 自动化

首次使用：

```bash
npm install
npx playwright install
```

本地配置按环境拆分为 `.env.fat` 和 `.env.uat`，两者使用同一份 [`.env.example`](.env.example) 模板并均被 Git 忽略。默认命令读取 `.env.fat`；UAT 必须显式设置 `--env .env.uat`（Python 入口）或 `ENV_FILE=.env.uat`（UI/npm 入口），避免跨环境复用链接或账号。

单个环境文件至少配置：

```bash
CLIENT_BASE_URL=https://client-fat.filbet2025.com
CLIENT_PHONE=<client phone>
CLIENT_PASSWORD=<client password>
PLAYWRIGHT_CHANNEL=
```

常用命令：

```bash
npm run test:ui:p0
npm run test:ui:p0:scan
npm run test:ui:network-discovery
npm run test:ui:p0:pn
npm run test:ui:inventory
npm run test:ui:login
npm run test:ui:deposit-contract
npm run test:ui:game-bet
npm run ui:p0-points
```

- `npm run test:ui:p0`：执行客户端 P0 UI 默认套件，包含登录正反例、主流程扫描、游戏启动冒烟、页面状态正反例；默认不做真实资金动作。
- `npm run test:ui:p0:scan`：只执行 Playwright P0 客户端主流程扫描用例。
- `npm run test:ui:network-discovery`：窗口化 Playwright Network 发现入口，固定 Pixel 7 手机浏览器格式，登录后探索 P0 页面、充值、提现、Transaction、Bet History 等入口，生成脱敏 JSON、HAR、trace 与 Markdown 报告；只用于接口发现和人工确认，不纳入默认 CI 门禁。
- `npm run test:ui:p0:pn`：只执行客户端 P0 UI 正反例补充用例。
- `npm run test:ui:inventory`：按 `ui/data/client-pages.json` 扫描客户端页面定位资产，输出 `ui/reports/client-locator-inventory.md`。
- `npm run test:ui:login`：执行客户端登录正反例。
- `npm run test:ui:deposit-contract`：安全验证充值页的支付方式和金额控件；默认不创建充值订单。
- `npm run test:ui:game-bet`：登录后进入配置的游戏页；默认只验证启动，设置 `EXECUTE_BET=true` 才点击游戏内投注区域。
- `npm run ui:p0-points`：根据 `ui/data/client-p0-test-points.json` 生成客户端 P0 UI 测试点报告。
- UI 原始 JSON、截图、视频索引在 `ui/results/`，默认不提交 Git。
- `PLAYWRIGHT_CHANNEL` 默认留空，使用 Playwright 自带 Chromium；需要指定本机 Chrome 时再设置为 `chrome`。

## 使用原则

- 先完善规划，再分阶段落地。
- 先做 P0 核心链路，再扩展 P1、P2。
- API P0 资产放在 `api/p0/`；UI 用例、配置、报告分别放在 `ui/cases/`、`ui/data/`、`ui/reports/`。
- `api/results/`、`ui/results/`、`ui/reports/`、`playwright-report/`、`test-results/` 都是可再生成产物目录，只保留最近一次结果。
- 敏感信息不提交到 Git。
- 测试账号、Token、Cookie、环境变量使用本地配置或 CI 凭据管理。
