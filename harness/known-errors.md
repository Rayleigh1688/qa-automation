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
| `/admin/finance/deposit/risk/list` | 接口文档标 GET，实际 GET 返回 405；POST 无 body 会出现 CBOR EOF 或业务失败 | 使用 POST + CBOR body 传查询参数 |
| `/admin/finance/withdraw/risk/audit/list` | 接口文档标 GET，实际 GET 返回 405；POST 无 body 会出现 CBOR EOF 或业务失败 | 使用 POST + CBOR body 传查询参数 |
| `/admin/finance/deposit/manual/success` | 接口文档标 GET，实际 GET 返回 405；POST 后业务返回 `invalid verification code`；已接入本地 TOTP 后仍失败 | 需要抓后台真实补单请求，确认验证码字段、校验通道或前置流程 |

## 后台 token 失败

现象：

- 后台登录或后台只读接口 HTTP 200。
- 业务返回 `status=false`。
- 错误内容和 token、字段类型或登录态相关。

已定位原因：

- 缺少 `x-device-id`。
- `google_code` 被作为字符串发送，后端期望数字。
- 曾误加 `t:` token 前缀，前端实际使用裸 token。
- 曾把业务失败响应里的字符串误判为 token。

处理：

- 使用 `api/runbooks/ADMIN.md` 的后台登录规范。
- 确保 `ADMIN_DEVICE_ID` 从浏览器真实请求注入。
- runner 只在 `status=true` 时提取 token。

## FAT 偶发 502

现象：

- 财务类接口偶发返回 nginx `502 Bad Gateway`。
- 立即重试可能恢复。

处理：

- 不直接修改断言放宽。
- 记录发生时间和接口。
- 连续失败再判定环境或服务问题。

## 敏感信息风险

风险：

- smoke result JSON 可能包含 token、账号字段、响应样本。
- 浏览器抓包可能包含 cookie、设备 id、token。

处理：

- `api/*-smoke-result.json` 不提交。
- `.env` 不提交。
- 文档只写占位符，不写真实凭据、cookie、token、设备 id。
