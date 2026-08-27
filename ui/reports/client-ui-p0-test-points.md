# 客户端 P0 UI 测试点

## 原则

- P0 UI 只覆盖接口自动化无法完整证明的客户端主流程状态、入口、前置校验和第三方页面链路
- 接口文档可稳定覆盖的纯接口断言继续放在 API P0，UI 不重复堆断言
- 活动、运营位、Rewards 和 Filcoin 的玩法细节变化频繁，只做页面可达和 Network 可见性，不纳入稳定回归细节
- 真实投注、真实充值、真实提现属于资金变更动作，不进入默认 P0；必须通过显式开关或人工确认执行
- 所有 UI 用例必须数据驱动，路由、弹窗、游戏点击点、测试点清单分别维护在 ui/data 下

## 测试点

| ID | 模块 | 类型 | 执行方式 | 测试点 | 路由 | 自动化状态 | Spec |
|---|---|---|---|---|---|---|---|
| UI-P0-001 | 登录注册 | positive | default_auto | 手机号 OTP 登录成功 | `/` | implemented | ui/cases/client-login.spec.mjs |
| UI-P0-002 | 登录注册 | negative | default_auto | 空手机号不能提交登录 | `/` | implemented | ui/cases/client-login.spec.mjs |
| UI-P0-003 | 登录注册 | negative | default_auto | 无效手机号不能登录 | `/` | implemented | ui/cases/client-login.spec.mjs |
| UI-P0-004 | 登录注册 | negative | default_auto | 未填写 OTP 不能登录 | `/` | implemented | ui/cases/client-p0-positive-negative.spec.mjs |
| UI-P0-005 | 登录注册 | negative | default_auto | 未勾选登录条款不能登录 | `/` | implemented | ui/cases/client-p0-positive-negative.spec.mjs |
| UI-P0-006 | 首页 | positive | default_auto | 首页可打开且主导航存在 | `/` | implemented | ui/cases/client-main-flow.spec.mjs |
| UI-P0-007 | Game | positive | default_auto | 登录后进入 Game 页面 | `/s-game-category-v2/gameType/3` | implemented | ui/cases/client-main-flow.spec.mjs |
| UI-P0-008 | Rewards | positive | default_auto | Rewards 页面可达 | `/welfare` | implemented | ui/cases/client-main-flow.spec.mjs |
| UI-P0-009 | Filcoin | positive | default_auto | Filcoin 页面可达 | `/s-points-v2` | implemented | ui/cases/client-main-flow.spec.mjs |
| UI-P0-010 | My | positive | default_auto | 登录后 My 页面展示会员身份和主入口 | `/my` | implemented | ui/cases/client-p0-positive-negative.spec.mjs |
| UI-P0-011 | My | negative | default_auto | 未登录访问 My 不应展示会员敏感信息 | `/my` | implemented | ui/cases/client-p0-positive-negative.spec.mjs |
| UI-P0-012 | 钱包 | positive | default_auto | 登录后钱包余额、充值、提现入口可见 | `/my` | implemented | ui/cases/client-p0-positive-negative.spec.mjs |
| UI-P0-013 | 充值 | positive | manual_or_next_auto | 充值页可打开并展示渠道和金额 | `/my` | planned |  |
| UI-P0-014 | 充值 | negative | manual_or_next_auto | 充值缺少金额或渠道时不能提交 | `/my` | planned |  |
| UI-P0-015 | 投注 | positive | default_auto | 登录后进入可控游戏并验证启动成功 | `/s-game-page/17453858840928` | implemented | ui/cases/client-game-bet-smoke.spec.mjs |
| UI-P0-016 | 投注 | positive | gated_auto | 固定视口下点击 Lucky Penny Spin 并捕获投注请求 | `/s-game-page/17453858840928` | implemented_gated | ui/cases/client-game-bet-smoke.spec.mjs |
| UI-P0-017 | 投注 | negative | default_auto | 无效游戏页不能启动三方游戏 | `/s-game-page/invalid-p0-game-id` | implemented | ui/cases/client-p0-positive-negative.spec.mjs |
| UI-P0-018 | 提现 | positive | manual_or_next_auto | 提现页可打开并展示前置规则 | `/my` | planned |  |
| UI-P0-019 | 提现 | negative | manual_or_next_auto | 提现缺少金额、账号或钱包密码时不能提交 | `/my` | planned |  |
| UI-P0-020 | KYC | positive | default_auto | My 或 Account Center 展示 KYC 状态 | `/my` | covered | ui/cases/client-p0-positive-negative.spec.mjs |

## 断言明细

### UI-P0-001 手机号 OTP 登录成功

- 执行方式: default_auto
- 自动化状态: implemented
- 对应用例: `ui/cases/client-login.spec.mjs`
- 首页登录入口可访问
- 手机号、OTP、条款控件可定位并可操作
- 提交后进入已登录态，不再展示 Register / Login
- Network 捕获会员登录、会员详情或钱包相关接口

### UI-P0-002 空手机号不能提交登录

- 执行方式: default_auto
- 自动化状态: implemented
- 对应用例: `ui/cases/client-login.spec.mjs`
- 手机号为空时 Login 按钮不可用，或提交后仍停留登录态
- 不能进入会员态
- 不能出现会员详情或钱包成功响应

### UI-P0-003 无效手机号不能登录

- 执行方式: default_auto
- 自动化状态: implemented
- 对应用例: `ui/cases/client-login.spec.mjs`
- 无效手机号提交后仍停留登录或游客态
- 页面不进入会员态
- 不能出现会员详情或钱包成功响应

### UI-P0-004 未填写 OTP 不能登录

- 执行方式: default_auto
- 自动化状态: implemented
- 对应用例: `ui/cases/client-p0-positive-negative.spec.mjs`
- 已填写手机号但 OTP 为空时不能完成登录
- Login 按钮不可用或点击后仍停留登录态
- 不能出现会员详情或钱包成功响应

### UI-P0-005 未勾选登录条款不能登录

- 执行方式: default_auto
- 自动化状态: implemented
- 对应用例: `ui/cases/client-p0-positive-negative.spec.mjs`
- 手机号和 OTP 已填写但未同意条款时不能完成登录
- Login 按钮不可用或点击后仍停留登录态
- 不能出现会员详情或钱包成功响应

### UI-P0-006 首页可打开且主导航存在

- 执行方式: default_auto
- 自动化状态: implemented
- 对应用例: `ui/cases/client-main-flow.spec.mjs`
- 首页加载成功且不出现 Page not found
- 登录入口或会员态信息可见
- Game、Rewards、Filcoin、My 至少能通过导航或配置路由到达

### UI-P0-007 登录后进入 Game 页面

- 执行方式: default_auto
- 自动化状态: implemented
- 对应用例: `ui/cases/client-main-flow.spec.mjs`
- Game 页面可达
- 不出现 Page not found
- 捕获游戏列表、游戏配置或游戏启动相关 Network

### UI-P0-008 Rewards 页面可达

- 执行方式: default_auto
- 自动化状态: implemented
- 对应用例: `ui/cases/client-main-flow.spec.mjs`
- Rewards 页面可打开
- 不出现 Page not found
- 活动细节只记录可见性和 Network，不做稳定细节断言

### UI-P0-009 Filcoin 页面可达

- 执行方式: default_auto
- 自动化状态: implemented
- 对应用例: `ui/cases/client-main-flow.spec.mjs`
- Filcoin 页面可打开
- 不出现 Page not found
- 积分活动细节只记录可见性和 Network，不做稳定细节断言

### UI-P0-010 登录后 My 页面展示会员身份和主入口

- 执行方式: default_auto
- 自动化状态: implemented
- 对应用例: `ui/cases/client-p0-positive-negative.spec.mjs`
- My 页面可打开
- 会员账号、KYC、充值、提现或钱包入口至少可见一组
- Network 捕获会员详情或钱包相关接口

### UI-P0-011 未登录访问 My 不应展示会员敏感信息

- 执行方式: default_auto
- 自动化状态: implemented
- 对应用例: `ui/cases/client-p0-positive-negative.spec.mjs`
- 新浏览器上下文直接访问 My
- 未登录时应展示登录入口、游客态或跳回首页
- 不能展示会员账号、UID、KYC Approved、钱包余额等敏感会员信息

### UI-P0-012 登录后钱包余额、充值、提现入口可见

- 执行方式: default_auto
- 自动化状态: implemented
- 对应用例: `ui/cases/client-p0-positive-negative.spec.mjs`
- 余额或钱包入口可见
- 充值入口可见或可通过 My 页面进入
- 提现入口可见或可通过 My 页面进入
- 钱包相关接口返回成功

### UI-P0-013 充值页可打开并展示渠道和金额

- 执行方式: manual_or_next_auto
- 自动化状态: planned
- 充值入口可打开
- 充值渠道、金额输入或金额快捷选项可定位
- 创建订单前置参数可从 Network 捕获
- 默认 P0 不提交真实充值订单

### UI-P0-014 充值缺少金额或渠道时不能提交

- 执行方式: manual_or_next_auto
- 自动化状态: planned
- 未选择渠道或未填写金额时提交按钮不可用
- 提交后展示明确校验提示
- 不能生成有效充值订单

### UI-P0-015 登录后进入可控游戏并验证启动成功

- 执行方式: default_auto
- 自动化状态: implemented
- 对应用例: `ui/cases/client-game-bet-smoke.spec.mjs`
- 游戏页可打开
- 出现第三方游戏 frame 或游戏域名
- 默认不点击真实投注按钮
- Network 捕获游戏启动相关请求

### UI-P0-016 固定视口下点击 Lucky Penny Spin 并捕获投注请求

- 执行方式: gated_auto
- 自动化状态: implemented_gated
- 对应用例: `ui/cases/client-game-bet-smoke.spec.mjs`
- 必须显式设置 EXECUTE_BET=true
- 固定视口 1366x768
- 点击配置的相对坐标后捕获 play、spin、bet、wager 或 process 请求
- 最终资金结果以后续投注记录或钱包账变接口为准

### UI-P0-017 无效游戏页不能启动三方游戏

- 执行方式: default_auto
- 自动化状态: implemented
- 对应用例: `ui/cases/client-p0-positive-negative.spec.mjs`
- 无效游戏页不应出现有效第三方游戏 frame
- 页面应展示 Page not found、错误态或保持客户端壳页
- 不能触发真实投注请求

### UI-P0-018 提现页可打开并展示前置规则

- 执行方式: manual_or_next_auto
- 自动化状态: planned
- 提现入口可打开
- 账户、金额、钱包密码或前置校验控件可定位
- 展示可提现余额、手续费或限制信息
- 默认 P0 不提交真实提现申请

### UI-P0-019 提现缺少金额、账号或钱包密码时不能提交

- 执行方式: manual_or_next_auto
- 自动化状态: planned
- 缺少必要参数时按钮不可用或展示明确校验提示
- 不能产生有效提现申请
- 失败原因需要同步沉淀到接口测试参数规则

### UI-P0-020 My 或 Account Center 展示 KYC 状态

- 执行方式: default_auto
- 自动化状态: covered
- 对应用例: `ui/cases/client-p0-positive-negative.spec.mjs`
- 登录后可进入 My 或 Account Center
- KYC 状态可见或会员详情接口可返回 KYC 状态
- 不在 UI 默认用例内提交 KYC 资料
