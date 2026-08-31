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

KYC 提交和审核流程资料复杂，第一轮暂缓；UI 层只保留入口、状态和可见性检查。

## 下一周期重点

1. 先增加窗口化 Playwright 的脱敏 Network 摘要、HAR 和 trace 捕获，将原始证据保存在 `ui/results/`。
2. 以已跑通的登录、充值和游戏启动为基础，依次探索 KYC 入口/状态、提现入口、真实下注、下注结果和派彩展示。
3. 三方游戏内部操作继续使用 Pixel 7 `412x915` 固定视口下的 Playwright + 相对坐标；每次操作同时保存截图和 Network 证据，便于定位接口版本变化。
4. API 不替代真实下注操作：UI 证明三方游戏内可完成真实交互，API 负责核对游戏入口、投注记录、账变和派彩结果。

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
npm run test:ui:game-bet
npm run ui:p0-points
```

所有 npm UI 命令执行前都会清空 UI 生成物目录，只保留最近一次结果。

- `npm run test:ui:network-discovery`：窗口化 Playwright Network 发现入口，固定 Pixel 7 手机浏览器格式，登录后探索首页、Game、Rewards、Filcoin、My、充值、提现、Transaction、Bet History、KYC、账户入口；输出脱敏 JSON、HAR、trace 和 Markdown 报告，只用于接口发现，不纳入默认 CI 门禁。

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
- KYC 是 P0 主流程 UI 专项：新账号首页默认弹出 KYC 引导，二次确认后进入 `/s-kyc-v2`，依次完成证件/图片、地址、个人信息、核对提交并看到 `KYC successful`。成功提示只表示已提交等待处理，不等于后台审核通过。
- KYC 新账号池使用 `090XXXXXXXX`，首个账号从 `09000000001` 开始，测试环境 OTP 固定 `111111`；已驳回/未通过 KYC 的账号可再次提交。
