# P0 Main Flow Write Smoke Report

生成时间：`2026-08-26`

## 执行范围

- 环境：FAT
- 执行器：`scripts/api-controlled-flow-runner.py`
- 结果文件：`api/results/controlled-write-result.json`
- 请求编码：CBOR
- TLS：测试环境临时使用 `--insecure`

这是 P0 主流程写操作冒烟，不是 P0 之外的低优先级任务。它和只读 P0 门禁分开执行，是为了避免每次 CI 都创建订单或冻结资金。

`api/results/controlled-write-result.json` 每次覆盖刷新，并且不提交仓库。报告只保留脱敏结论。

## 结果概览

| 流程 | 结果 | 说明 |
| --- | --- | --- |
| 新增用户 | 通过 | 随机测试手机号 + FAT OTP 注册成功，返回 token 和 `is_reg=1` |
| 客户端登录 | 通过 | `/member/sms` + `/member/otp/login/v2` API 登录成功，返回客户端 token |
| 后台登录 | 通过 | `/admin/login/auth` + `/admin/login` API 登录成功，返回后台 token |
| 创建充值订单 | 通过 | 使用充值 `mode=1` 的 GCash 通道和标准档位，返回 `order_id` 和支付链接 |
| 后台充值列表 | 通过 | `/admin/finance/deposit/risk/list` 真实方法为 POST，查询参数需要放 CBOR body |
| 后台充值补单 | 未通过 | `/admin/finance/deposit/manual/success` 真实方法为 POST，但需要额外补单验证码，当前返回 `invalid verification code` |
| 创建提现申请 | 未通过 | 提现账户、余额、KYC 基础条件存在，但接口业务返回失败且错误信息为空 |
| 后台提现审核列表 | 通过 | `/admin/finance/withdraw/risk/audit/list` 真实方法为 POST，查询参数需要放 CBOR body |

## 未调通项

| 流程 | 当前状态 | 已排除 | 下一步 |
| --- | --- | --- | --- |
| 充值补单 | 未调通 | 接口方法、鉴权、订单号、CBOR 编码已确认 | 抓后台真实补单请求，确认补单验证码字段和值来源 |
| 提现申请 | 未调通 | 余额、withdrawable、KYC、提款账户基础条件都存在 | 抓前端真实提现请求，确认是否需要资金密码、流水限制、风控规则、单日限额、未完成订单限制或隐藏参数 |

## 已确认规则

| 规则 | 结论 |
| --- | --- |
| 注册短信 | `/member/sms` 注册场景 `reason` 可为空 |
| 注册接口 | `/member/register` 使用 `otp_id`、`code`、`password`、`invite_code`、`i` |
| 充值通道 | `/finance/channel/list?mode=1&source=huawei` 才是充值通道 |
| 提现通道 | `/finance/channel/list?mode=2&source=huawei` 是提现通道 |
| 充值下单 | `/finance/payment/deposit` 可以创建测试订单，需选择真实可用通道和档位 |
| 后台充值审核列表 | 文档标 GET，实际应按 POST + CBOR body 执行 |
| 后台充值补单 | 文档标 GET，实际应按 POST 执行，且需要额外验证码 |
| 后台提现审核列表 | 文档标 GET，实际应按 POST + CBOR body 执行 |
| 提现申请 | `/finance/payment/withdraw` 当前还缺少可通过的业务前置或接口规则 |

## 调试记录

### 注册

成功：

- `POST /member/sms`
- `POST /member/register`

断言：

- HTTP 200。
- 业务 `status=true`。
- 注册响应包含 token。
- `is_reg=1`。

### 充值

失败尝试：

- 使用 `mode=2` 的提现通道作为 `pid` 下单，返回 `Payment channel unavailable`。
- 使用 QRPH 充值通道最低金额 10，下单返回 `Deposit failed, please contact customer service!`。

成功尝试：

- 使用 GCash 充值通道。
- 金额使用通道标准档位。
- 返回 `order_id` 和支付链接。
- 后台登录成功。
- 后台充值审核列表接口可查询成功，但刚创建的三方支付订单未进入 risk/list。

报告不保存完整支付链接。

后台补单：

- `POST /admin/finance/deposit/manual/success`
- Body 已尝试：`id`、`desc`、`code`、`google_code`。
- 已接入本地 `ADMIN_APPROVAL_TOTP_SECRET` 动态生成 6 位码。
- 当前业务仍失败：`invalid verification code`。
- 判断：补单接口使用的验证码字段、校验通道或前置流程仍需以后台真实补单请求为准，不能只按 Bruno 文档猜字段。

### 提现

失败尝试：

- Maya 账户金额 1，返回 `Withdrawal amount is below the minimum allowed`。
- Maya 账户金额 10，返回业务失败且错误信息为空。
- Maya 账户金额 100，返回业务失败且错误信息为空。
- GCash 账户金额 200，返回业务失败且错误信息为空。

已排除的基础条件：

- 测试账号钱包余额充足。
- `withdrawable` 大于测试提现金额。
- KYC 详情接口可查，`kyc_status=5`。
- 提款账户列表存在可用 GCash 和 Maya 账户。

下一步需要从前端真实提现请求或后端业务规则确认是否还需要资金密码、流水限制、提现通道风控、单日限额、未完成订单限制或其他隐藏参数。

## 最新执行命令

充值下单 + 后台补单调试：

```bash
CLIENT_PHONE=<client phone> CLIENT_OTP=<otp code> \
ADMIN_EMAIL=<admin email> ADMIN_PASSWORD=<admin password> ADMIN_GOOGLE_CODE=<google code> ADMIN_DEVICE_ID=<x-device-id> \
python3 scripts/api-controlled-flow-runner.py \
  --deposit \
  --approve-deposit \
  --approval-code <approval code> \
  --insecure \
  --body-format cbor \
  --deposit-amount 10 \
  --out api/results/deposit-positive-flow-result.json
```

主流程正向调试：

```bash
CLIENT_PHONE=<client phone> CLIENT_OTP=<otp code> \
ADMIN_EMAIL=<admin email> ADMIN_PASSWORD=<admin password> ADMIN_GOOGLE_CODE=<google code> ADMIN_DEVICE_ID=<x-device-id> \
python3 scripts/api-controlled-flow-runner.py \
  --main-positive-flow \
  --insecure \
  --body-format cbor \
  --deposit-amount 10 \
  --withdraw-amount 100 \
  --out api/results/main-positive-flow-result.json
```
