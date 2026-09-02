# UI 自动化说明

## 定位

UI 自动化用于补足 API 无法证明的真实用户路径、页面集成状态和第三方游戏/canvas 场景。

当前只聚焦客户端 P0 主流程；后台管理端优先通过 API 验证，暂不建设后台 UI 回归。

## 目录分工

| 目录 | 用途 |
| --- | --- |
| `ui/cases/` | Playwright 测试用例 |
| `ui/data/` | 页面、弹窗、P0 测试点、游戏点击点等数据配置 |
| `ui/elements/` | 页面对象和业务操作封装 |
| `ui/framework/` | 环境读取、Network 记录、定位辅助、通用动作 |
| `ui/reports/` | UI 最近一次 Markdown 可读报告 |
| `ui/results/` | UI 最近一次 JSON、截图、trace、视频等原始结果 |

`ui/reports/` 和 `ui/results/` 是可再生成产物目录，不作为长期手册或固定资产。

## 当前 P0 范围

- 登录注册。
- 首页和主导航。
- 游戏入口和投注链路探针。
- 钱包、充值、提现入口与状态。
- My/个人中心。

KYC 在默认 UI 门禁中只验证入口和状态可见；真实资料提交由受控专项完成，后台审核和审核后状态刷新由 API 证明。证件/OCR/eKYC/驳回重提矩阵归 P1。

## 当前收口重点

1. 默认 UI 套件补齐充值页安全前置，不创建真实资金订单；Maya 合法提现和未 KYC 提现拦截均使用独立受控 UI 用例。
2. 真实投注继续使用 Pixel 7 `412x915` 固定视口和配置化相对坐标；单注读取 `CLIENT_GAME_BET_AMOUNT`（FAT 1000、UAT 100），投注次数由流水查询结果决定。
3. UI 证明三方游戏内真实交互；API/数据库只读核对投注记录、账变、流水和提现订单，不能用启动请求代替业务金额断言。
4. Network discovery、HAR 和 trace 只用于接口版本发现与排障，不作为默认 P0 通过条件。

UAT 真实投注使用 BNG `Coins`（`/s-game-page/17453859148937`），环境单注上限为 100。脚本先点击游戏空白区域收起客户端侧栏，再打开投注额面板、选择 100 并点击 Spin；UAT 专用 Jili `Super Ace 2` 配置已移除，FAT 原有游戏配置保持不变。

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
```

`npm run test:p0` 为 API safe/negative + 默认 UI 的可重复门禁；`npm run test:p0:full` 才会显式执行真实资金主流程。完整入口先用新号执行 KYC 前提现拦截，再提交 KYC；资金账号统一复用 API session 与 UI storage state，并在投注后轮询流水，归零后才提交提现。

完整资金链在 UI 投注和流水归零后恢复由 API 创建提现订单并完成后台关联。Maya UI 提现独立证明客户端可选择渠道、输入金额和生成订单，不作为 API CTC-009 的替代结果。

提现金额下限属于 API 业务契约：使用有效提款账户传入小于通道最小值的金额，并断言不能生成订单。UI 不重复承担该后端边界矩阵，只验证合法金额输入、提交动作以及本次提现订单确实生成。

受控提现 UI 使用独立命令 `npm run test:ui:withdraw-contract`。FAT 默认先选择 `CLIENT_WITHDRAW_CHANNEL=Maya`，GCash 当前会返回 `Payment channel unavailable`。默认只验证非法金额不会发请求；显式设置 `EXECUTE_WITHDRAW_UI=true` 时还需要本地 `CLIENT_WALLET_PASSWORD`，脚本通过页面数字键盘输入后提交合法金额。钱包密码只能放在忽略的 `.env.fat` / `.env.uat` 或 CI 凭据中；UAT UI 命令必须设置 `ENV_FILE=.env.uat`。

永久未 KYC 账号的提现拦截使用 `npm run test:ui:unverified-withdraw`。账号通过 `PRE_KYC_CLIENT_PHONE` 和 `PRE_KYC_CLIENT_PASSWORD` 注入；该账号绝不提交 KYC 或设置钱包密码。用例断言 Security Requirements 同时要求钱包密码和 KYC，且没有创建提现请求。

所有 npm UI 命令执行前都会清空 UI 生成物目录，只保留最近一次结果。

`npm run test:ui:p0` 固定 `--workers=1`。除刚注册且尚未设置登录密码的账号外，所有既有账号默认使用密码登录；OTP 只用于注册、首次设置密码等必要步骤。当前全局准备在没有有效状态时使用密码登录，登录与 token 生命周期的进一步简化留到下一步统一处理。

- `npm run test:ui:network-discovery`：窗口化 Playwright Network 发现入口，固定 Pixel 7 手机浏览器格式，登录后探索首页、Game、Rewards、Filcoin、My、充值、提现、Transaction、Bet History、KYC、账户入口；输出脱敏 JSON、HAR、trace 和 Markdown 报告，只用于接口发现，不纳入默认 CI 门禁。
- `npm run test:ui:deposit-contract`：验证充值页、支付方式和金额控件；默认不创建订单，只有显式 `EXECUTE_DEPOSIT_CONTRACT=true` 时才提交并捕获非活动充值请求。

需要单独清理 UI 产物：

```bash
python3 scripts/clean-test-artifacts.py ui
```

## 结果规则

- UI 可读报告：`ui/reports/*.md`。
- UI 原始结果：`ui/results/*.json`。
- UI 截图、trace、视频：`ui/results/` 或 Playwright 附件目录。
- Playwright HTML 报告：`playwright-report/`。
- Playwright 测试附件：`test-results/`。

这些目录不提交历史报告；需要历史追踪时使用 CI 归档。

## Network 发现协作规则

- 自动化优先捕获同一 Playwright browser context 内页面、iframe、弹窗和新标签页请求；只有普通 Playwright 事件无法说明问题时，再用 DevTools 或人工浏览器补充。
- `ui/results/client-network-discovery.json` 保存脱敏后的原始事件和 endpoint 汇总，`ui/reports/client-network-discovery-report.md` 保存可读候选接口表。
- 若自动化未能打开充值、提现、KYC、银行卡或记录入口，由熟悉业务的同学指出真实入口文案、页面路径或固定视口下可点击区域，再沉淀到 `ui/data/`。
- 第三方页面、资料上传、真实资金动作和真实投注不默认执行；需要执行时必须显式开启对应环境变量或单独专项用例。
- 测试环境页面加载最多等待 5 秒；超过 5 秒记录为加载过慢 warning，除非登录成功或关键入口存在等硬前置不满足。
- My 页 `Withdraw` 为提现入口，`Deposit` 为充值入口，`Transaction` 可查看充值、提现和账变记录，`Bet History` 为投注记录入口。
- 充值页 `Multiple Deposit Bonus` 活动开关默认不参加；参加活动会产生提现流水限制。
- KYC 最小 UI 提交保留在 P0：新账号首页默认弹出 KYC 引导，二次确认后进入 `/s-kyc-v2`，依次完成证件/图片、地址、个人信息、核对提交并看到 `KYC successful`。扩展证件、OCR/eKYC 和驳回重提矩阵归 P1。
- KYC 新账号池使用 `090XXXXXXXX`，首个账号从 `09000000001` 开始，测试环境 OTP 固定 `111111`；已驳回/未通过 KYC 的账号可再次提交。
