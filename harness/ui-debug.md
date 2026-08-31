# UI Debug

## 用途

记录 UI 自动化测试调试方法。

## 调试记录

### Playwright 与当前客户端定位方式

- 当前客户端大量控件是自定义 `div/svg/button` 组合，不是标准表单控件。
- Playwright 不适合直接套 Selenium 式 XPath 大量硬找节点；优先使用 role、text、placeholder、name、aria-label 和配置化 selector。
- 如果控件没有稳定语义属性，可以用 DOM 派生定位：先找到稳定文本所在容器，再点其内部目标元素。不要写死绝对坐标。

### PAGCOR 弹窗

- 弹窗 DOM：`[data-family-name="pagcor"]`。
- `I agree to all ...` 不是标准 checkbox input，而是 SVG 自定义控件。
- 处理方式：在 modal 内找到 `innerText` 以 `I agree to all` 开头的容器，点击该容器的第一个子元素，再点击 `Proceed`。
- 如果 `Proceed` 明明可见可用但被 `role=alert` 遮挡，先正常 click，失败后允许对按钮执行 DOM click 兜底。
- 不要把 `PAGCOR` 作为弹窗 detectText。首页/页脚也可能出现 PAGCOR，容易误判弹窗仍存在。

### 登录入口

- 首页 `/` 是主要入口，但不一定直接展示登录表单。
- 登录封装先进入首页并处理弹窗，再点击 `Register / Login` / `Login` / `Register`。
- 只有出现手机号输入框或 `SMS OTP` tab 才认为登录页打开成功。
- `/login` 在当前 FAT 客户端会返回 404，不要把候选路径列表的最后一个地址当作最终可用路由。
- 登录提交成功后不要立刻再次自动处理营销/合规弹窗。已验证这会让主流程扫描偶发进入 PWA 错误页。

### 主导航扫描

- 客户端 PWA 的主导航优先点击页面上的导航文案，不要直接用旧接口文档或旧路由猜地址。
- 当前扫描识别到的新版主路由：
  - Game: `/s-game-category-v2/gameType/3`
  - Rewards: `/welfare`
  - Filcoin: `/s-points-v2`
  - My: `/my`
- `/slots`、`/bonus`、`/coin`、`/user` 等旧候选路径会进入 `Page not found` 壳页，只能作为历史参考。
- 普通 role/link/button 定位失败时，可以使用 DOM 派生文本点击，查找可见文本元素后执行原生 click。

### 游戏内投注

- 三方游戏在 iframe/canvas 内渲染，Playwright 基本拿不到稳定 DOM locator。
- 当前策略：项目内 Playwright 自行启动 Chromium，负责登录、打开游戏、等待 frame ready、截图和 Network；不依赖 Codex 内置浏览器是否已有可连接实例。
- 客户端和三方游戏统一使用 Pixel 7 `412x915`。游戏、调额和 Spin 的有效相对坐标只维护在 `ui/data/client-game-actions.json`，本文件不再复制坐标值。
- 冒烟脚本默认不点击真实投注，必须显式设置 `EXECUTE_BET=true`。
- 是否投注成功不只看截图，至少结合第三方 `/b/server` 的 `command: play` 请求、钱包余额或投注记录接口判断。
- Beanstalk 已验证可把业务单注固定为 1000；`scripts/run-turnover-bet.py` 根据只读流水汇总计算点击次数，并在投注后复查总剩余流水。
- UI 可读报告统一写入 `ui/reports/`；原始 JSON、截图统一写入 `ui/results/`，不再写入 `api/`。
- UI 结果目录只保留最近一次执行产物。每次执行可以覆盖或清空 `ui/results/`、`ui/reports/`、`playwright-report/`、`test-results/`；不要按时间戳或次数在工作区累积报告。
- 如果发现历史 UI 产物在 `api/results/`，需要迁移到 `ui/results/`，避免 API 和 UI 执行结果混放。

### P0 UI 正反例套件

- `npm run test:ui:p0` 是客户端 P0 UI 默认套件，覆盖登录正反例、主流程扫描、游戏启动冒烟和页面状态正反例。
- `npm run test:ui:p0:scan` 只跑主流程页面扫描。
- `npm run test:ui:p0:pn` 只跑正反例补充用例。
- 默认 P0 不执行真实下注、真实充值、真实提现。真实下注必须显式设置 `EXECUTE_BET=true`。
- P0 UI 测试点源数据是 `ui/data/client-p0-test-points.json`，可读报告由 `npm run ui:p0-points` 生成到 `ui/reports/client-ui-p0-test-points.md`。
- 正反例执行报告写入 `ui/reports/client-p0-positive-negative-report.md`，原始 JSON 写入 `ui/results/client-p0-positive-negative.json`。

### 登录页条款

- 登录页的 `I agree to the Terms of Use ... confirm that I am 21 years old` 也是自定义控件。
- 处理方式：找到该文案容器，点击容器左侧区域，再验证 `Login` 按钮是否启用。
- 反例必须显式保持未勾选，不能为了让按钮可点而调用正例的条款点击 helper。2026-08-31 FAT 实测未勾选仍能完成 OTP 登录，当前作为产品缺陷保留失败。

### 登录会话复用

- 默认 P0 固定 1 worker。主账号只在无有效 storage state 时登录一次；后续用例加载 `ui/results/client-p0-storage-state.json`。
- API/UI 交替时使用 `export-browser-p0-session.py`、`import-api-p0-session.py` 同步同一个 token，不得重新登录。
- 清理结果时必须保留忽略的 UI storage state 和 API session；否则清理动作会意外触发新登录并使另一进程 token 失效。

### Get Code 定位

- 不要使用 `/Get Code|Send|OTP|Code/i` 这种过宽正则。
- 过宽正则会优先命中 `SMS OTP` tab，导致没有真正请求 OTP。
- 当前使用精确匹配：`/^Get Code$|^Send$|^发送$|^获取$/i`。

### 登录正例断言

- 不能只断言页面操作无异常。
- 必须断言离开 `/login`，并捕获关键接口：
  - `/member/sms`
  - `/member/otp/login/v2`
  - `/member/detail`
  - `/finance/wallet`

### 已跑通命令

```bash
npm run test:ui:inventory
npm run ui:p0-points
npm run test:ui:login
```
