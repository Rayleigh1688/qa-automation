# UI 自动化说明

## 定位

UI 自动化用于补足 API 无法证明的真实用户路径、页面集成状态和第三方游戏/canvas 场景。

默认套件聚焦客户端P0主流程，P0的API与核心UI自动化继续维护。新需求API自动执行、UI人工验收，暂不新增UI脚本；早期[Telegram需求专项UI](../docs/telegram-qa.md)仅保留兼容，不扩展默认P0套件。

## 目录分工

| 目录 | 用途 |
| --- | --- |
| `ui/cases/` | Playwright 测试用例 |
| `ui/data/` | 页面、弹窗、P0 测试点、默认执行清单、游戏点击点等数据配置 |
| `ui/elements/` | 页面对象和业务操作封装 |
| `ui/framework/` | 环境读取、Network 记录、定位辅助、通用动作 |
| `ui/reports/` | UI 最近一次 HTML/Markdown 可读报告 |
| `ui/results/` | UI 最近一次 JSON、截图、trace、视频等原始结果 |

`ui/reports/` 和 `ui/results/` 是可再生成产物目录，不作为长期手册或固定资产。

## 当前 P0 范围

- 登录注册。
- 首页和主导航。
- 游戏入口和投注链路探针。
- 钱包、充值、提现入口与状态。
- My/个人中心。

默认 UI 的会员页用例使用钱包/会员/KYC等候选信息判断会员态，不保证单独断言KYC状态可见；已新增独立受控 KYC UI 提交用例，执行与限制见下文；本轮联网证据统一见交接。完整组合中的KYC提交/审核走受控API，不能作为KYC UI通过证据。证件/OCR/eKYC/驳回重提矩阵归 P1。

## 受控 KYC UI 最小链路

```bash
ENV_FILE=.env.fat npm run test:ui:kyc
ENV_FILE=.env.fat npm run test:ui:kyc -- --approve
# 仅续跑最近一小时同 runId、已 UI 提交且已审核成功的最后刷新
ENV_FILE=.env.fat npm run test:ui:kyc -- --resume-refresh
```

该入口独立于默认 10 条页面回归及原 `test:p0:full`，当前仅支持 FAT 测试资料。使用 `KYC_CLIENT_PHONE` / `KYC_CLIENT_PASSWORD` fresh UI 登录；账号必须与 `PRE_KYC_CLIENT_PHONE`、`WRITE_CLIENT_PHONE` 分离，证件读取忽略的 `KYC_IMAGE`。三个服务 URL 必须都属于指定 FAT 环境。历史 UI 专项的表单能力已迁入 `ui/elements/client-kyc.page.mjs`，定位与测试字段在 `ui/data/client-kyc-flow.json`，运行时不依赖归档。

用例只接受提交前 `kyc_status=0`：页面选择证件类型、上传三张资料、填写地址/个人信息、核对并点击 Submit；在 Submit 阶段逐次校验三次上传和提交响应，要求 HTTP 成功且业务 `status=true`、页面显示 `KYC successful`，刷新后同 UID 状态为 2。结果为 `SUBMITTED_PENDING`，不等于审核通过。待审或已通过账号均阻断本轮提交正例，不改判 PASS，也不自动驳回重置。日期选择沿用历史专项的成人默认值并校验至少 21 岁；控件变化或 eKYC 额外要求须实测调整，不自动跳过。

`--approve` 仅在上述本轮 UI 证据通过后，复用现有 `kyc-approve` API 操作，按捕获的 UID 精确审核；使用实时审批 TOTP，随后 fresh UI 登录再读取同 UID 为 5 才记 `APPROVED`（API 登录可能使之前 UI 会话失效）。`--resume-refresh` 仅允许续跑最近一小时本轮已提交/已审核的最后刷新，校验 runId、原状态 0→2、三次上传及页面成功证据；不会把历史已通过账号算作新提交。该命令不充值或提现。KYC 表单不录制证件截图、视频或 trace；脱敏阶段结果位于 `ui/results/client-kyc-submit.json`，运行状态与可读报告分别为 `ui/results/kyc-ui-run-status.json`、`ui/reports/kyc-ui-report.html`。只覆盖该专项产物，不清掉其他业务阶段结果；会话文件在结束时删除。失败退出非零，写操作不自动重试。

后续资金状态衔接仍使用独立 `WRITE_CLIENT_*` 普通会员：UI 充值订单 → 按本次订单后台补单/到账核对 → 复用真实 UI 投注及流水检查 → UI 提现订单 → 同 UID/金额/订单号前后台对账。独立 KYC 号通过不能替代资金号的 KYC/钱包密码/绑定账户/余额前置。新的受控 UI 资金总入口见下一节；既有 `test:p0:full` 仍由 API 创建充值和提现，不能标记 UI 全流程通过。充值与提现专项已增加业务响应、金额及订单 ID 校验，后续接入必须传递本轮 ID，不能再次调用 API 建单来补证据。

## 受控 UI 业务总入口

```bash
# 只登录和读前置，不创建资金订单
npm run test:ui:business -- --env .env.fat
# KYC UI + 审核后，独立资金号完成 UI 充值/投注/提现及对账
npm run test:ui:business -- --env .env.fat --execute --clear-remaining-turnover --deposit-amount 1200 --withdraw-amount 1000
# 衔接刚完成的 KYC UI（从 kyc-ui-run-status.json 取得 runId，不读取历史 token）
npm run test:ui:business -- --env .env.fat --execute --clear-remaining-turnover --kyc-run-id <current-kyc-run-id>
```

默认仅输出 READY/BLOCKED 前置结论；`--execute` 才会创建订单。当前仅 FAT，充值上限 1200、提现上限 1000；同一个 `WRITE_CLIENT_*` 完成全部资金动作，KYC/BASIC 账号分离，BET/WITHDRAW 会话显式映射至资金账号。资金账号须已 KYC、有有效提款账户/钱包密码、无遗留流水。默认先执行独立 KYC UI；显式 `--kyc-run-id` 只关联最近一小时同 ID 的 UI 提交、审核和刷新成功证据。

充值和提现必须由 Playwright 实际页面产生订单；API 支持模块 `scripts/ui_fund_flow.py` 负责 fresh 登录、只读查询、本次 UI 充值单补单、新 KYC 号准备及显式流水清零，不创建充值/提现单。充值页未展示活动控件时，以实际请求的非活动参数判断，不假称点击过 Skip Bonus。补单前核对订单 ID、资金 UID、金额；到账增量必须精确等于 UI 充值额。

真实投注复用既有游戏专项及定位资产，受控模式要求 3–5 笔已结算付费投注，之后按显式参数执行后台清流，详见下节。投注后用本次新增已结算注单的投注额、净输赢对钱包变化；提现前再次核对流水为 0、可提现余额足够，再走 Maya UI 提交。最后按 UI 订单号匹配前后台 UID/金额/待审状态，并将本次新增账变逐条对后台 ID/金额/前后余额及全流程钱包差额。分页或异步结果不足会阻断，不用成功 API 建单补证据。

状态/原始 UI 证据在 `ui/results/`，可读报告 `ui/reports/ui-business-report.html` 复用公共模板，API 支持证据在 `api/results/ui-fund-support.json`。新一轮开始时复用公共清理器覆盖旧 UI 结果、报告、截图、视频与 trace；同一轮各阶段保留前序产物，失败停止后续动作。`--resume-run <runId>` 仅续跑最近一小时、尚未尝试补单的本轮充值后台关联失败；必须原 UI 订单 ID/非活动证据一致且余额和账变数量未改变，跳过重新建单。已补单成功但尚未投注、因明确空注单基线形状停止时，也可校验同订单精确到账且余额未变后续跑投注前基线；该分支强制跳过建单和补单。任何补单失败均不能重试写操作。它与默认 10 条回归、原跨 API/UI `test:p0:full` 分开报告。提现待审只证明成功提交，不证明最终出款。最新实测范围与未完成阶段见 [交接](../AI-HANDOFF.md)。

## 固定付费投注与显式清流（独立执行）

受控入口不需要 AI 或人工看图：本地安装 Node/npm、Python 3、Playwright Chromium、ImageMagick 7（`magick`）及 Tesseract（英文识别），并在忽略的环境文件配置 FAT 服务、各账号 lane、测试 KYC 素材及真实审批 TOTP。执行前会检查视觉依赖，缺失则停止。

```bash
# 只读前置检查，允许显式纳入专用资金号的遗留流水
npm run test:ui:business -- --env .env.ui-p0.fat --clear-remaining-turnover --allow-existing-turnover
# 新建独立 KYC 测试号，然后完成 UI KYC、充值、3 笔付费投注、清流、UI 提现和对账
npm run test:ui:business -- --env .env.ui-p0.fat --execute --new-kyc-account --bet-spins 3 --clear-remaining-turnover --allow-existing-turnover --headed
```

`--bet-spins` 允许 3–5，默认 3；单注固定 100。`--clear-remaining-turnover` 是必要的独立写开关；`--allow-existing-turnover` 明确把指定资金账号旧流水纳入本次清流，默认不允许。`--new-kyc-account` 复用现有号码分配/注册能力，只准备新号，实际 KYC 仍经 UI 提交；不设置该参数时须提供本轮刚准备的独立 KYC 新号，不复用上一轮账号。注册属于 API 数据准备，不算 UI 注册通过。`--headed` 仅影响显示方式，CI 可不传。不得对失败运行直接重放充值或审批。

Lucky Penny 的启动文字、按钮颜色特征、截图区域及等待参数统一在 `ui/data/client-game-actions.json` 的 `roundState`。普通投注最小点击间隔 2000ms；免费局/忙碌状态每 5000ms 复查、最长 60000ms，超时截图并非零退出。识别包含免费文字、背景、普通按钮特征和转轴稳定性；未知画面一律等待而不盲点。免费局结算后的未知继续弹窗目前也会超时停止，不猜坐标。

每次 UI 点击后还用同一浏览器会话只读查询已结算付费记录，必须新增恰好一笔 100 才继续；没有接受证据不自动补点。零投注派奖另计，最后核对钱包净变动。累计达到目标且画面恢复后，先证明流水下降，再调用公共后台清流/TOTP 能力并复核为零，随后 UI 创建提现单。报告分别记录投注前流水、投注后流水、后台清零后流水，不把管理动作算作自然投注完成。状态 JSON 和 HTML 仍位于原报告路径，默认页面回归入口不变。

充值钱包到账后，投注前还会每 5 秒查询后台流水，最长等待 60 秒：必须按本轮充值订单号关联唯一存款流水，并核对资金 UID、充值金额及未消耗状态，再保存投注基线。旧流水或暂时查询到 0 都不能代替该基线；超时不投注。状态文件保留每次基线查询摘要及清流前后读数，即使断言失败也能在报告中显示实际值。失败轮次若留下未清流水，新一轮仅在显式传入 `--allow-existing-turnover` 后才可将其纳入专用账号清流。

Mac/Linux 业务入口为每个执行阶段建立独立进程组，结束、失败或收到 Ctrl+C/SIGTERM 时清理该阶段的浏览器子进程，正常退出等待最多 3 秒后终止残留；下一阶段/下一轮按需重新启动。该清理不匹配或关闭日常 Chrome，也不影响其他独立测试进程组。直接强杀主 runner（SIGKILL）或系统崩溃无法执行退出清理。 Windows 使用 Job Object 隔离并终止本阶段后代，重构后仍需 Windows 清理专项回归；强制中断不保证报告落盘，详见 [本机运行锁与平台边界](../docs/local-running.md#本机运行锁)。

后台流水查询按每页 100 条读取全部页，核对总数、记录 ID 去重和资金 UID；页间总数变化、缺页或超过 100 页均阻断，不能使用部分结果清流。最终账变对账允许后台同步延迟：缺少本轮记录时每 5 秒只读复查、最长 60 秒；已有记录金额或前后余额不一致立即失败，不重放资金操作。

## 当前收口重点

1. 默认 UI 套件补齐充值页安全前置，不创建真实资金订单；Maya 合法提现和未 KYC 提现拦截均使用独立受控 UI 用例。
2. 真实投注使用 Pixel 7 `412x915` 固定视口和配置化相对坐标；FAT/UAT 单注均读取 `CLIENT_GAME_BET_AMOUNT=100`。默认次数由只读流水结果动态决定；完整入口也可用 `--bet-spins` 显式指定固定次数。
3. UI 证明三方游戏内真实交互；API/数据库只读核对投注记录、账变、流水和提现订单，不能用启动请求代替业务金额断言。
4. Network discovery、HAR 和 trace 只用于接口版本发现与排障，不作为默认 P0 通过条件。

FAT 真实投注使用 Lucky Penny，UAT 固定 `/s-game-page/17453859148937` 启动 BNG `Coins`，两者业务单注均为 100。UAT 同一 ID 曾短暂映射到错误游戏，开发修复后已重新通过无 Spin 身份门禁并完成真实投注。

游戏启动断言是投注前硬门禁：固定 `CLIENT_GAME_ID`/路由打开后，只要配置中的厂商或游戏标识未命中，Playwright 立即以 `configured game launch mismatch` 失败。此类失败直接报产品/环境 BUG，不自动搜索或尝试其他游戏，也不会执行投注额选择、Spin、流水处理或提现。2026-09-02 开发修复后，同一 UAT 配置的无 Spin 启动门禁已恢复通过。

## 定位策略

- 优先使用 role、text、placeholder、label、aria-label 和稳定属性。
- 自定义 `div/svg/button` 控件可以通过文本容器做 DOM 派生定位。
- 三方游戏 iframe/canvas 内部操作使用固定视口下的 Playwright + 相对坐标点击。
- 客户端页面和三方游戏页固定使用 Pixel 7 手机浏览器格式 `412x915`；三方游戏 iframe/canvas 点击坐标配置放在 `ui/data/client-game-actions.json`。

## 执行命令

```bash
npm run test:ui:p0
npm run test:ui:p0:scan
npm run test:ui:network-discovery
npm run test:ui:p0:pn
npm run test:ui:inventory
npm run test:ui:login
npm run test:ui:deposit-contract
npm run test:ui:game-bet
npm run test:ui:withdraw-contract
npm run test:ui:unverified-withdraw
npm run ui:p0-points
npm run test:p0
npm run test:p0:full
ENV_FILE=.env.fat npm run test:p0:full -- --bet-spins 10 --clear-remaining-turnover --deposit-amount 1200 --withdraw-amount 1000
python3 scripts/run-p0-tests.py --mode full --env .env.fat --scope FAT --deposit-amount 1200 --bet-spins 10 --clear-remaining-turnover --withdraw-amount 1000 --headed
```

`npm run test:p0` 为 API safe/negative + 默认 UI 的可重复门禁；`npm run test:p0:full` 执行完整资金主流程。完整入口先用永久 BASIC 账号验证提现拦截，再对独立 KYC 账号提交或复核 KYC；每次 UI 命令重新登录，storage state 只在本次 Playwright suite 内共享。默认会按剩余流水投注到 0；显式使用 `--bet-spins N --clear-remaining-turnover` 时，Playwright 固定投注 N 次并确认流水下降，随后管理后台清空剩余流水，复查为 0 后才提交提现。

Python UI/完整入口默认以 headless Chromium 运行；传 `--headed` 后，global setup、未 KYC 提现、默认 UI 和真实投注使用的 Playwright 浏览器都会在桌面显示，不需要设置 `PWDEBUG=1`，也不会额外打开 Inspector。

完整资金链在 UI 投注和流水归零后由 API 创建提现订单并完成后台关联。固定次数模式必须在报告中同时保留投注前、投注后和后台清流后的流水值，不能把后台清流冒充为投注自然完成。Maya UI 提现独立证明客户端可选择渠道、输入金额和生成订单，不作为 API CTC-009 的替代结果。

提现金额下限属于 API 业务契约：使用有效提款账户传入小于通道最小值的金额，并断言不能生成订单。UI 不重复承担该后端边界矩阵，只验证合法金额输入、提交动作以及本次提现订单确实生成。

受控提现 UI 使用独立命令 `npm run test:ui:withdraw-contract`。FAT 默认先选择 `CLIENT_WITHDRAW_CHANNEL=Maya`，GCash 当前会返回 `Payment channel unavailable`。默认只验证非法金额不会发请求；显式设置 `EXECUTE_WITHDRAW_UI=true` 时还需要本地 `CLIENT_WALLET_PASSWORD`，脚本通过页面数字键盘输入后提交合法金额。钱包密码只能放在忽略的 `.env.fat` / `.env.uat` 或 CI 凭据中；UAT UI 命令必须设置 `ENV_FILE=.env.uat`。

永久未 KYC 账号的提现拦截使用 `npm run test:ui:unverified-withdraw`。账号通过 `PRE_KYC_CLIENT_PHONE` 和 `PRE_KYC_CLIENT_PASSWORD` 注入；该账号绝不提交 KYC 或设置钱包密码。用例断言 Security Requirements 同时要求钱包密码和 KYC，且没有创建提现请求。

原有 npm UI 专项执行前会清空 UI 生成物目录；新增 KYC/业务总入口只覆盖本入口结果，保留同轮前序阶段证据。

`npm run test:ui:p0` 固定 `--workers=1`。每次命令由 global setup fresh login，并仅为本次 suite 写入 storage state；下次命令不会复用。FAT 既有账号默认使用密码登录；UAT 使用真实动态短信 OTP：UI 点击 Get Code，按客户端返回的同一 ID 从后台读取本次验证码，再由 UI 提交登录。固定 `111111` 不用于 UAT。

默认 10 条测试的固定清单位于 `ui/data/client-p0-default-suite.json`。报告器按文件名和英文执行标题核对实际 Playwright JSON，并通过清单中的 `group`、`displayName` 在主 HTML/Markdown 报告展示中文分组和中文 Case 名称；固定项未被收集时补记 `NOT_RUN`，整份报告不能判为 `PASS`。

- `npm run test:ui:network-discovery`：窗口化 Playwright Network 发现入口，固定 Pixel 7 手机浏览器格式，登录后探索首页、Game、Rewards、Filcoin、My、充值、提现、Transaction、Bet History、KYC、账户入口；输出脱敏 JSON、HAR、trace 和 Markdown 报告，只用于接口发现，不纳入默认 CI 门禁。
- `npm run test:ui:deposit-contract`：验证充值页、支付方式和金额控件；默认不创建订单，只有显式 `EXECUTE_DEPOSIT_CONTRACT=true` 时才提交并捕获非活动充值请求。

需要单独清理 UI 产物：

```bash
python3 scripts/clean-test-artifacts.py ui
```

## 结果规则

- UI 可读报告：`ui/reports/*.md`、`ui/reports/*.html`。
- UI 原始结果：`ui/results/*.json`。
- UI 截图、trace、视频：`ui/results/` 或 Playwright 附件目录。
- Playwright HTML 报告：`playwright-report/`。
- P0 UI 汇总报告：`ui/reports/p0-ui-report.html`，与 API、主流程报告共用相同模板，按本次 Playwright 用例统计 PASS/FAIL/SKIPPED。
- 完整组合报告：`api/results/p0-main-flow-report.html` 保留 8 条业务主流程结论，同时展示充值/投注/流水/提现摘要、关键执行轨迹、格式化统一核对、Playwright 页面截图和原始 JSON 链接。截图只证明页面状态与浏览器交互；资金和订单结论仍以结构化核对为准。
- 完整组合状态：`api/results/p0-full-run-status.json` 记录总编排状态、headed 模式、参数、失败/完成阶段和总时间；完整入口失败时仍覆盖生成 `BLOCKED` 主流程 HTML/Markdown，不保留上一轮成功页面冒充本轮结果。
- Playwright 测试附件：`test-results/`。

`npm run test:ui:p0` 在启动浏览器前检查环境文件、客户端 URL、FAT/UAT scope、认证变量、默认用例清单和 Playwright 依赖。统一状态写入 `ui/results/p0-ui-run-status.json`，记录最后阶段、开始/结束时间、退出码和脱敏错误；HTML 同时展示执行总耗时。global setup、浏览器启动、用例或未知异常失败时均以非零状态退出并判为 `BLOCKED`。若标准报告渲染脚本本身异常，runner 会把整体状态提升为 `FAILED`，并在同一路径写入最小 HTML/Markdown 兜底报告。

这些目录不提交历史报告；需要历史追踪时使用 CI 归档。

## Network 发现协作规则

- 自动化优先捕获同一 Playwright browser context 内页面、iframe、弹窗和新标签页请求；只有普通 Playwright 事件无法说明问题时，再用 DevTools 或人工浏览器补充。
- `ui/results/client-network-discovery.json` 保存脱敏后的原始事件和 endpoint 汇总，`ui/reports/client-network-discovery-report.md` 保存可读候选接口表。
- 若自动化未能打开充值、提现、KYC、银行卡或记录入口，由熟悉业务的同学指出真实入口文案、页面路径或固定视口下可点击区域，再沉淀到 `ui/data/`。
- 第三方页面、资料上传、真实资金动作和真实投注不默认执行；需要执行时必须显式开启对应环境变量或单独专项用例。
- 测试环境页面加载最多等待 5 秒；超过 5 秒记录为加载过慢 warning，除非登录成功或关键入口存在等硬前置不满足。
- My 页 `Withdraw` 为提现入口，`Deposit` 为充值入口，`Transaction` 可查看充值、提现和账变记录，`Bet History` 为投注记录入口。
- 充值页 `Multiple Deposit Bonus` 活动开关默认不参加；参加活动会产生提现流水限制。
- KYC 最小 UI 提交由独立 KYC/业务入口覆盖：新账号首页KYC引导→二次确认→`/s-kyc-v2`→证件/图片→地址→个人信息→核对提交→`KYC successful`。默认页面回归及旧 API/full 组合不能代替独立 KYC UI 执行证据。扩展证件、OCR/eKYC和驳回重提矩阵归P1。
- KYC 账号分配与验证码规则统一见 [环境手册](../api/runbooks/ENVIRONMENTS.md)。

## UI 报告的证据层

默认 `p0-ui-report.html` / `.md` 在固定用例结果之外展示执行摘要、中文用例轨迹、主导航页面观察、Network 响应计数、充值请求与真实 Spin 状态，以及本轮页面截图。证据不增加通过用例数；结构观察不能替代业务断言。

辅助结果只在本次 Playwright 时间窗口内关联；缺失或过期结果明确显示未采集，不用历史图片补齐。`p0-ui-evidence.json` 仅输出白名单摘要，不链接认证/storage state 或原始响应正文。截图可以点击原图；默认游戏启动截图不会被标为投注成功。报告可用 `python3 scripts/render-ui-p0-report.py` 从已有结果重新生成，不触发业务执行。

最终阶段的只读核对失败可使用 `npm run test:ui:business -- --env .env.ui-p0.fat --resume-reconcile <run-id>`：仅允许最近一小时同 runId、同资金 UID、已有本次 UI 提现单的检查点，不传 `--execute`，不重放任何 UI 或后台写动作。投注前的 `--resume-run` 还会要求本次到账余额、全部注单与原基线一致；已有投注后禁止重放。续跑完成会在报告中明确标记，不能表述为一次无中断运行通过。

## 业务报告断言与产物覆盖

`ui/reports/ui-business-report.html` 的“逐步骤断言”展示结果、核对项、期望值、实际值和证据字段；同一份结构化明细写入 `ui/results/ui-business-run-status.json` 的 `assertions`。断言从本轮订单、KYC runId、游戏时间窗口及 API 支持文件校验摘要关联；不读取凭据、完整响应或个人资料到 HTML。免费旋转未触发标记 `NOT_TRIGGERED`，步骤未执行标记 `NOT_RUN`，已执行但缺少明细标记 `NOT_RECORDED`，不能随阶段 PASS 批量补成通过。原运行 PASS 但断言证据冲突/缺失时，报告提示 `EVIDENCE_MISMATCH` / `EVIDENCE_INCOMPLETE`，不改写历史运行结论。

每次新的 `test:ui:business`（含只读前置检查）在开始时清理 `ui/results`、`ui/reports`、`playwright-report`、`test-results`，固定路径只保留最新一轮，不创建按日期累积的图片副本。API 侧只覆盖本流程的 `ui-fund-support.json` 和 `ui-kyc-approve.*`，不清除独立 API 报告。`--resume-run` / `--resume-reconcile` 属于同轮续跑，保留检查点及该轮附件；显式 `--kyc-run-id` 会先验证最近一小时同 ID 的成功证据，只保留两份必要 KYC JSON 后再清理其余旧 UI 产物。

仅更新现有报告、不运行测试或清理检查点：

```bash
python3 scripts/render-ui-business-report.py
```

该命令按已有证据重新生成断言明细和 HTML，不创建任何业务数据。报告不额外复制静态截图；默认页面回归仍使用自己的既有清理入口。

### 图片留证与图片断言

业务报告优先展示金额对账摘要和可放大的关键截图，再列出逐项断言。普通页面是“DOM/文字断言 + 截图留证”，图片本身不表示业务通过；游戏的按钮裁剪图是实际 OCR/特征匹配输入，记录区域、特征差异、阈值和转轴稳定性。`ready/free/busy` 各保存最近一次识别输入，另保存启动识别及超时现场，固定文件名覆盖，不按轮询次数累积图片。

截图元数据位于对应 UI JSON 的 `visualEvidence`：包含 runId、采集时间及 SHA256。报告拒绝跨轮、越界路径、过期和哈希不符的图片。旧版同订单截图仅在时间窗口内作为已有 UI 留证展示，不能升级成新的图片断言。缺失的图片明确注明未采集，不为补图重放业务。

KYC 仅截取配置白名单中的状态文字边界，证件表单、图片和个人资料不截图；找不到安全文字则记录 `NOT_CAPTURED`，不能拿接口状态生成伪造图片。审核页状态文字候选仍需后续真实运行验证。显式 `--kyc-run-id` 除两份 JSON 外，最多保留两张经过 runId/哈希及隐私类型校验的关联状态截图。新一轮清理规则保持不变。

## 团队本地配置与互斥

统一模板、个人凭据覆盖、账号分配和离线 doctor 见 [团队本地运行](../docs/local-running.md)。现有 npm UI 命令在清理前获取本机锁，直接 CLI 需使用 `npm run run:local -- <command>`。KYC 每轮用独立新号，BASIC 永久未认证，资金号按执行者分配；锁不提供跨机器保护。旧默认环境与结果路径保持兼容。

## 简洁用例与结果

新需求专项采用CSV用例、前置清单和四状态结果树，详见[用例与结果流程](../docs/testing-workflow.md)。旧历史结果已按用户授权清理，保留范围见当前交接；登录和数据准备不计业务PASS，脚本错误不直接计产品FAIL。

## 新需求固定UI执行

ISOP-2027使用`npm run qa:requirement -- ISOP-2027 --layer UI`离线校验；追加`--execute --insecure --allow-write kyc-review`执行已授权FAT专项。页面/元素固定于`ui/data/isop2027.json`，步骤与结果使用统一plan协议，产物隔离于`reports/qa/`且不由P0清理器处理。三图双账号流程与取证、会话说明见[阶段3记录](../docs/new-requirement-stage3.md)。

新需求的默认团队分工已调整为[API自动执行与UI人工验收](../docs/team-testing.md)。上述固定UI脚本仅保留兼容；当前不安排新需求UI自动化建设，P0的API与核心UI自动化继续维护。
