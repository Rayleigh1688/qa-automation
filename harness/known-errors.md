# Known Errors

## 用途

记录自动化测试中反复出现的问题、原因和处理方式。

## 问题列表

## HTTP 200 但业务失败

现象：

- HTTP 状态为 `200`。
- 响应可解码。
- `status=false`。

处理：

- 不允许判定通过。
- 优先记录 `data` 或错误消息。
- 如果是老接口，记录替代接口。

已知案例：

| 接口 | 现象 | 处理 |
| --- | --- | --- |
| `/member/game/list` | 历史曾 HTTP 200 但业务失败；2026-08-31 FAT 复验又返回 `status=true` | P0 仍以真实客户端使用的 `/member/v2/index`、`/member/game/listRw`、`/member/game/list/recommend` 为正例；旧接口只作兼容观察，不作为“必须失败”反例 |
| `/member/vip` | HTTP 200 但业务失败 | 使用 `/promo/vip/config`、`/promo/vip/sign/in/config` |
| `/finance/channel/product/list?mode=1&pid=1` | 业务返回 `Payment channel unavailable` | 不纳入 P0 safe smoke，等可用支付通道数据 |
| `/member/kyc/ekyc/url` | 当前测试账号返回 `Account Disabled` | 不纳入 P0 safe smoke，需账号/SDK 状态确认 |
| `/finance/payment/deposit` | 使用提现通道或不可用通道会返回 `Payment channel unavailable` 或 `Deposit failed` | 使用 `mode=1` 充值通道和标准档位 |
| `/finance/payment/deposit`（UAT） | 2026-09-02 GCash 在 1200/1000、QRPH/PESONET 在 1000 均返回 `Payment channel unavailable`；Maya 随后成功创建 1200 订单，后台同订单补单后钱包 193→1393 | UAT 充值正例固定使用已确认的 Maya PID；保留其他通道失败作为通道级异常，不再判定整个充值层阻塞 |
| UAT 游戏启动 | 固定 `/s-game-page/17453859148937` 曾进入错误厂商/游戏；开发修复后同一 ID 已恢复 BNG `Coins` | 仍保留投注前厂商/游戏硬门禁；再次不匹配时直接报产品/环境 BUG，不寻找替代游戏 |
| `/finance/payment/withdraw` | 资金账号流水清零后，GCash 仍返回 `Payment channel unavailable`；Maya 可成功创建提现单 | GCash 属于 FAT 通道不可用；当前正例创建阶段使用 Maya |
| `/finance/payment/deposit` | FAT 在 `amount=49`（通道最小 `50`）及 `amount=1000001`（通道最大 `1000000`）时仍返回成功并创建未审核充值单 | P0 限额校验缺陷；默认 CI 不执行该会创建订单的契约探针，修复后执行 `api-p0-negative-runner.py --include-deposit-limit-contract` 复验 |
| `/admin/finance/deposit/risk/list` | 接口文档标 GET，实际 GET 返回 405；POST 无 body 会出现 CBOR EOF 或业务失败 | 使用 POST + CBOR body 传查询参数 |
| `/admin/finance/withdraw/risk/audit/list` | 接口文档标 GET，实际 GET 返回 405；POST 无 body 会失败；秒级时间参数只能得到空页 | 使用 POST + CBOR；`start_time/end_time` 必须传毫秒时间戳，再按本次订单 id 本地精确匹配 |
| `/admin/finance/withdraw/agree` | Maya 提现单可进入 `under_review`，但 FAT 审核后订单变为 `canceled`，`cancel_reason=No available transfer interface` | 属于 FAT 出款接口未配置；`agree` 业务失败后 runner 必须停止，禁止继续调用 success 冒充闭环 |
| `/admin/finance/deposit/manual/success` | 接口文档标 GET，实际 GET 返回 405；补单必须使用 POST、CBOR 请求体和真实审批动态码 | 以受控 runner 的 POST 实现为准；如再次返回验证码错误，抓取后台真实请求核对字段和前置流程 |

## 后台 token 失败

现象：

- 后台登录或后台只读接口 HTTP 200。
- 业务返回 `status=false`。
- 错误内容和 token、字段类型或登录态相关。

已定位原因：

- 缺少 `x-device-id`。
- FAT 后台登录 `google_code` 固定为 `111111`，但仍必须按数字发送，后端不接受字符串形式。
- 曾误加 `t:` token 前缀，前端实际使用裸 token。
- 曾把业务失败响应里的字符串误判为 token。

处理：

- 使用 `api/runbooks/ADMIN.md` 的后台登录规范。
- 确保 `ADMIN_DEVICE_ID` 从浏览器真实请求注入。
- runner 只在 `status=true` 时提取 token。
- 管理后台审核动作使用真实动态 Google 令牌，不复用登录固定码 `111111`。

## FAT 偶发 502

现象：

- 财务类接口偶发返回 nginx `502 Bad Gateway`。
- 立即重试可能恢复。

处理：

- 不直接修改断言放宽。
- 记录发生时间和接口。
- 连续失败再判定环境或服务问题。

## FAT 管理后台英文界面中英混合

现象：

- 管理后台切换或显示为英文时，会员详情大部分菜单、字段和按钮为英文，但“流水要求调整”、调整类型的“增加/扣除/清零”等仍显示中文。
- 推荐人变更入口在英文页面显示为语义错误的 `changed`，实际打开的是“转移代理线”表单。
- 同一详情页可同时出现 `Credit or Debit`、`View Token Wallet` 等正常英文、残留中文和错误英文。

影响：

- 仅使用单一语言的 exact-text selector 会产生控件不存在的假阴性，进而漏掉真实接口。
- 不能根据 `changed` 等表面文案推断业务动作，必须结合字段上下文、弹窗标题和 Network 判断。

处理：

- 扫描资产保留当前 UI 原文，同时增加中英文/错误译文的语义别名；优先用描述项上下文、表单标题和稳定 DOM 层级定位。
- 不改用绝对坐标，也不把不同语言重复计算为两个接口。
- 当前确认范围为 FAT 管理后台会员详情；其他页面继续扫描，发现同类问题时追加页面与控件，不直接泛化为全站。

## FAT 管理后台并发登录使复用会话失效

现象：多个 Playwright 线程各自登录后再加载各自的 storage state，页面可能反复回落 `/user/login`；脚本看似没有填写账号密码，其实是在复用已被后续登录替换的 token。

处理：管理后台并行只读扫描先由 `admin-shared-session.mjs` 登录一次，将 mode `0600` 的 storage state 写入 `/tmp`，再用全新 context 验证 `/admin/me/detail` HTTP 200 / 业务成功。各线程只读取同一 state，禁止自行重新登录；写线程在只读线程结束后串行执行。加载后若回落登录页，立即以 `SESSION_INVALID` 停止，不循环重开页面。

### 会员通用充值倍率使用登录固定码时失败无提示（2026-09-03）

- 无效探针曾在 FAT 管理后台会员详情选择 `Custom` 并填写 1.0，但错误地把后台登录固定码当作业务审批码。
- `POST /admin/member/deposit/multiple/update` 返回 HTTP 200、业务 `status=false`；响应只有 `data/status`，弹窗保持打开且页面没有 message/notification。该现象可作为“无效业务码缺少可见错误说明”的诊断记录，但不能证明接口正例失败。
- 使用实时 Google TOTP 后，同一接口 HTTP 200、业务 `status=true`，成功把本轮 Custom 1.0 恢复为 Platform Configuration 1.5，操作记录共 2 条；接口最终归类 `ACTIVE`。
- 长期规则：FAT 固定 `111111` 仅用于登录；任何登录后的业务验证码必须使用实时 Google TOTP。

## FAT 客户端手机号限制

现象：

- `/member/sms` HTTP 200。
- 业务返回 `status=false`。
- `data` 为 `This mobile number has been restricted. Please contact customer support.`。

影响：

- 客户端登录前置无法获取新的 `otp_id`。
- API 正例 smoke、反例 runner 和 UI 登录都会受影响。

处理：

- CI 使用稳定的专用客户端账号，避免频繁触发短信限制。
- 反例 runner 在 `api_all` 流程中可复用刚刚正例 smoke 的客户端 token，减少重复短信请求。
- 当前 runner 已改为强制复用 `p0-api-session.json`，负例阶段不再执行第二次成功登录；同一账号的 UI 套件也固定串行复用 storage state。
- 如果正例 smoke 一开始就无法登录，需要更换客户端测试账号或解除该手机号限制。

## FAT/UAT 未勾选登录条款仍可登录

现象：

- FAT 登录页保持条款未勾选，填写有效 OTP 后仍请求 `/member/otp/login/v2`。
- 2026-09-02 UAT 使用永久 BASIC 账号的密码登录复现：未勾选条款仍请求 `/member/v2/login`，随后 `/member/detail` 与 `/finance/wallet` 均成功，页面进入会员态并出现 BASIC/KYC 引导。
- 两个环境的接口均返回成功并进入会员态。

判断：

- 不是定位器误点；Playwright Network 和登录后 KYC 引导页均已确认。
- P0 UI 反例必须继续失败，不能通过自动勾选条款或放宽断言隐藏该问题。

处理：

- 默认仍作为 UI 缺陷保留失败，不放宽断言。2026-09-02 用户明确接受本轮临时例外后继续 UAT 受控资金链；报告必须显示 UI 10/11 和该例外，不能写成 UI 全通过。

## 提款账户列表返回空数据

现象：

- `/finance/account/list` HTTP 200 且 `status=true`。
- 当前只读账号返回 `data=null`，而不是提款账户列表。

诊断：

- 如果同一账号重复查询都返回 `data=null`，按账号未绑定提款账户处理。
- 2026-09-01 UAT 首次完整 safe smoke 中出现过一次 `data=null`，但该候选此前单接口返回 2 条，随后同账号单接口复验及同 token 连续 5 次采样也都返回 2 条。这次结果暂记为未确认的 UAT 响应波动，不能反推账号未绑定，也不能用自动重试覆盖原始失败。

影响：

- `TC-022` 无法通过，提现入口和提款账户关联也不能用该账号完成。
- 这是测试账号前置不满足，不应放宽为接受 `null`，否则会掩盖成熟账号缺少提款账户的数据问题。

处理：

- 为 `CLIENT_PHONE` 配置已绑定提款账户的成熟只读账号；资金主流程账号另按 `api/p0/README.md` 的资金链放行规则执行。
- 候选已由后台证明具备提款前置时，保留失败轮原始结果，再以相同 token 连续只读采样确认响应类型；整套门禁仍按原始严格断言失败，待后续完整复跑和服务端节点排查。

## 三方游戏请求金额不能作为最终投注金额

现象：

- 游戏启动或会话 `/process/` 请求中的 `total_bet` 与页面最终选择的单次投注金额不一致。
- UI 已选择 1000 且钱包、投注账变均扣除 1000，但该请求字段不能提供相同断言。
- 2026-09-02 FAT Lucky Penny 实测页面单注和账变均为 1000，而第三方请求值为 100000，属于协议内部缩放，不是实际下注 100000。

处理：

- 网络字段只作为观察信息，不作为金额硬断言。
- 以投注前后页面、钱包变化、Bet History、资金账变和流水累计交叉确认本次投注。
- `ui/data/client-game-actions.json` 对 Lucky Penny 和 UAT BNG Coins 设置 `assertRequestedBetAmount=false`；厂商请求中的缩放值不作为最终业务金额断言，真实金额继续由投注记录、钱包、账变和流水交叉证明。

## 流水提现被更早的业务校验拦截

现象：

- 同一账号充值 1200 后产生流水 1800，真实投注 1000 后剩余流水 800。
- 投注输掉后余额仅 300，API 提现 1000 先返回 `Insufficient balance`，没有创建提现单。
- 另一个余额和剩余流水均充足、提款账户与平台记录看似可用的普通会员，FAT 仍先返回 `Payment channel unavailable`，也没有创建提现单。

2026-08-31 最新复验：

- `9888888050` 使用真实 UI 固定单注 1000 完成 6 注后，全部未完成流水由 5750 降为 0；钱包 `locked=0`、`withdrawable=884376.46`。
- GCash 创建提现返回 `Payment channel unavailable`，无订单、无余额变化。
- Maya 创建 1000 提现成功，订单 `88033033545903082` 进入 `under_review`，钱包暂扣 1000。
- 后台审核时因 `No available transfer interface` 被取消，金额自动退回，钱包恢复；这证明客户端提现创建已通，但 FAT 出款/审核环境尚未形成正向闭环。
- 客户端提现列表能按同一订单号返回 `amount=1000,status=canceled`，但子状态为 `approval=0,payout=0`；数据库对应值为 `approval=1,payout=3`。需确认客户端接口是否有意归一化内部审核/出款状态，未确认前不做这两个字段的一致性通过断言。

影响：

- 当前环境尚不能用错误文案证明“还差 800”，但数据库流水状态和无提现副作用可以证明限制仍存在。
- 不应为了匹配文案放宽金额、绕过通道或直接改库。

处理：

- 提现前同时检查余额、withdrawable、locked、提款账户和通道可用性。
- 流水限制反例的核心断言为业务拒绝、无新提现单、无错误冻结；具体错误文案记录为辅助证据。
- FAT 通道可用性与后台配置不一致需要后端进一步定位。

## 充值基础流水与活动流水叠加规则

现象：

- UI 在充值页关闭 `Multiple Deposit Bonus`，确认 `Skip Bonus? → Yes` 后，真实请求为 `cashback_flag=0&rotation_flag=0`。
- 订单落库为 `activity_id=0`、`product_id` 空、`rollover_multiplier=0`，说明活动确实未参加。
- FAT 后台对该订单执行手工补单成功后，仍新增 `ty=3（存款）` 流水：充值 1000 对应流水 1500。
- 同一账号历史非活动充值也稳定出现 10→15、50→75，说明不是单次脏数据。

确认规则：

- `rotation_flag` 映射正确：0 为不参加，1 为参加；当前 1.5 倍不是因为自动化传错 flag。
- 不论是否参加活动，充值都会产生普通存款基础流水；Skip Bonus 只是不叠加活动流水，不等于零流水。
- 参加活动时，在存款基础流水之外继续叠加活动对应的流水要求。
- 在规则确认前，自动化必须分别记录活动选择、订单 `activity_id` 和最终 `fb_members_turnover.ty`，不能只根据请求 flag 判定无流水。

## 敏感信息风险

风险：

- smoke result JSON 可能包含 token、账号字段、响应样本。
- 浏览器抓包可能包含 cookie、设备 id、token。

处理：

- `api/results/`、`ui/results/`、`ui/reports/`、`playwright-report/`、`test-results/` 只保留最近一次生成物，不提交历史报告。
- `.env` 不提交。
- 文档只写占位符，不写真实凭据、cookie、token、设备 id。
