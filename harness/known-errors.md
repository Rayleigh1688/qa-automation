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
| `/member/game/list` | HTTP 200 但业务失败 | 使用 `/member/v2/index`、`/member/game/listRw`、`/member/game/list/recommend` |
| `/member/vip` | HTTP 200 但业务失败 | 使用 `/promo/vip/config`、`/promo/vip/sign/in/config` |
| `/finance/channel/product/list?mode=1&pid=1` | 业务返回 `Payment channel unavailable` | 不纳入 P0 safe smoke，等可用支付通道数据 |
| `/member/kyc/ekyc/url` | 当前测试账号返回 `Account Disabled` | 不纳入 P0 safe smoke，需账号/SDK 状态确认 |
| `/finance/payment/deposit` | 使用提现通道或不可用通道会返回 `Payment channel unavailable` 或 `Deposit failed` | 使用 `mode=1` 充值通道和标准档位 |
| `/finance/payment/withdraw` | 当前测试账号提现申请业务失败，部分场景错误信息为空 | 需要确认资金密码、流水、通道风控或隐藏参数 |
| `/finance/payment/deposit` | FAT 在 `amount=49`（通道最小 `50`）及 `amount=1000001`（通道最大 `1000000`）时仍返回成功并创建未审核充值单 | P0 限额校验缺陷；默认 CI 不执行该会创建订单的契约探针，修复后执行 `api-p0-negative-runner.py --include-deposit-limit-contract` 复验 |
| `/admin/finance/deposit/risk/list` | 接口文档标 GET，实际 GET 返回 405；POST 无 body 会出现 CBOR EOF 或业务失败 | 使用 POST + CBOR body 传查询参数 |
| `/admin/finance/withdraw/risk/audit/list` | 接口文档标 GET，实际 GET 返回 405；POST 无 body 会出现 CBOR EOF 或业务失败 | 使用 POST + CBOR body 传查询参数 |
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
- 如果正例 smoke 一开始就无法登录，需要更换客户端测试账号或解除该手机号限制。

## 敏感信息风险

风险：

- smoke result JSON 可能包含 token、账号字段、响应样本。
- 浏览器抓包可能包含 cookie、设备 id、token。

处理：

- `api/results/`、`ui/results/`、`ui/reports/`、`playwright-report/`、`test-results/` 只保留最近一次生成物，不提交历史报告。
- `.env` 不提交。
- 文档只写占位符，不写真实凭据、cookie、token、设备 id。
