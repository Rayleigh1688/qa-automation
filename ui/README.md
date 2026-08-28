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

- 以已跑通的登录、充值、游戏启动为基础，探索一个稳定场馆的真实下注操作、下注结果和派彩展示。
- 三方游戏内部操作继续使用固定 `1366x768` 视口下的 Playwright + 相对坐标；每次操作同时保存页面截图和 Network 摘要，便于定位场馆接口版本变化。
- API 不替代真实下注操作：API 负责核对游戏入口、投注记录、账变和派彩结果；UI 负责证明用户在三方游戏内可完成真实交互。

## 定位策略

- 优先使用 role、text、placeholder、label、aria-label 和稳定属性。
- 自定义 `div/svg/button` 控件可以通过文本容器做 DOM 派生定位。
- 三方游戏 iframe/canvas 内部操作使用固定视口下的 Playwright + 相对坐标点击。
- 当前固定视口基线为 `1366x768`；坐标配置放在 `ui/data/client-game-actions.json`。

## 执行命令

```bash
npm run test:ui:p0
npm run test:ui:p0:scan
npm run test:ui:p0:pn
npm run test:ui:inventory
npm run test:ui:login
npm run test:ui:game-bet
npm run ui:p0-points
```

所有 npm UI 命令执行前都会清空 UI 生成物目录，只保留最近一次结果。

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
