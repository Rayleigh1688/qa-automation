# UI Testing Skill

## 用途

指导 AI 或测试执行者维护、扩展和执行本项目的 UI 自动化资产。

当前 UI 自动化只聚焦客户端主流程，不追活动细节；后台管理端优先用 API 覆盖，暂不建设后台 UI 回归。

适用范围：

- 客户端 Playwright 主流程测试。
- 客户端页面定位资产扫描。
- 客户端登录注册、首页、游戏入口、钱包、充值、提现、个人中心等 P0 UI 测试点。
- 用 UI 补足接口文档无法说明的前置规则、页面状态、按钮可用性和真实 Network 链路。

## 规则

1. UI 自动化不要替代 API P0。API 负责快速稳定的核心接口门禁，UI 负责真实用户路径、前端集成风险和接口无法证明的规则。
2. 客户端 UI 只封装主流程测试点：
   - 登录注册。
   - 首页。
   - Game/投注入口。
   - 钱包。
   - 充值。
   - 提现。
   - My/个人中心。
3. 活动、运营位、临时弹窗、Rewards 细节、Filcoin 活动玩法默认不做稳定 UI 回归，只记录可见性和 Network。
4. 后台管理端暂不做 UI 自动化。后台登录、报表、列表、详情、审批查询优先走 API。
5. UI 脚本必须数据驱动：
   - 页面和路由配置放 `ui/data/client-pages.json`。
   - 弹窗规则放 `ui/data/client-modals.json`。
   - P0 UI 测试点放 `ui/data/client-p0-test-points.json`。
   - 游戏固定视口和相对点击点放 `ui/data/client-game-actions.json`。
   - 用例只编排流程，不把页面文案、路由候选、弹窗规则散落到测试逻辑里。
6. Playwright 定位优先级：
   - `getByRole`、`getByLabel`、`getByPlaceholder`、`getByText`。
   - 稳定属性：`data-testid`、`data-test-id`、`name`、`placeholder`、`aria-label`。
   - 配置化 CSS selector。
   - 对自定义 SVG/div 控件，可使用 DOM 派生定位：先从语义文本找到容器，再计算目标元素位置点击。
   - 三方游戏 iframe/canvas 无稳定 DOM 时，允许固定 `1366x768` 视口下的相对坐标；坐标必须配置在 `ui/data/client-game-actions.json`，不得散落在用例代码。
7. 登录态、storage state、截图、视频、trace、token、cookie、账号和 OTP 不提交仓库。UI 原始结果写入 `ui/results/`，默认忽略。
8. UI 可读报告写入 `ui/reports/`，原始 JSON、截图、trace、视频写入 `ui/results/`；Playwright HTML 和测试附件分别写入 `playwright-report/`、`test-results/`。
9. UI 结果目录只保留最近一次执行产物。npm UI 命令会先执行 `python3 scripts/clean-test-artifacts.py ui`，不要在工作区按时间戳或次数累积报告。
10. UI 失败时先判断是：
   - 页面选择器变化。
   - 接口返回异常。
   - 测试数据状态不满足。
   - 环境网络或证书问题。
   - 第三方 iframe、支付页、KYC SDK 等外部依赖。
11. 对稳定 UI 用例，断言应该同时覆盖：
   - 页面关键元素出现。
   - 核心文案或数据正确。
   - 关键 API 请求成功。
   - 用户下一步操作可继续。
12. 正例断言不能只看 Playwright 动作不报错。必须证明业务结果，例如：
    - 登录正例必须离开登录页，并捕获 `/member/otp/login/v2`、`/member/detail` 或钱包接口。
    - 提现专项不能只点按钮，要捕获按钮状态、禁用原因、前置校验和提现接口请求。
    - 游戏专项先证明进入游戏或启动接口，不默认执行真实下注。

## 目录和命令

核心资产：

- `playwright.config.mjs`
- `ui/cases/`
- `ui/data/`
- `ui/elements/`
- `ui/framework/`
- `ui/README.md`

最近一次生成物：

- `ui/reports/*.md`
- `ui/results/*.json`
- `ui/results/screenshots/`
- `playwright-report/`
- `test-results/`

常用命令：

```bash
npm run test:ui:inventory
npm run ui:p0-points
npm run test:ui:login
npm run test:ui:p0
npm run test:ui:p0:scan
npm run test:ui:p0:pn
npm run test:ui:game-bet
```

## 当前基线

- 定位资产扫描已跑通：`npm run test:ui:inventory`。
- P0 UI 测试点报告可通过 `npm run ui:p0-points` 生成，测试点源数据为 `ui/data/client-p0-test-points.json`。
- 客户端登录正反例已跑通：`npm run test:ui:login`。
  - OTP 登录成功。
  - 空手机号不能登录。
  - 无效手机号停留登录页。
- 客户端 P0 默认套件命令：`npm run test:ui:p0`。
- 客户端主流程扫描命令：`npm run test:ui:p0:scan`。
- P0 UI 正反例补充套件命令：`npm run test:ui:p0:pn`。
  - 未填写 OTP 不能登录。
  - 未勾选条款不能登录。
  - 未登录访问 My 不暴露会员敏感信息。
  - 登录后 My 展示会员、钱包、充值、提现或 KYC 入口。
  - 无效游戏页不启动第三方游戏。
- Lucky Penny 游戏投注冒烟已跑通：`EXECUTE_BET=true npm run test:ui:game-bet`。

## 下一步

1. 做钱包、充值、提现入口专项扫描。
2. 用提现页真实 UI 状态反推接口层 `/finance/payment/withdraw` 失败原因。
3. 将投注冒烟的 UI 点击结果接入投注记录、钱包账变 API 断言。
4. 补充第二个可控游戏，验证固定视口和相对坐标策略是否可复用。
