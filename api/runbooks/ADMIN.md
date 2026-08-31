# Admin API Runbook

上级入口：[`API.md`](API.md) 和 [`api/p0/README.md`](../p0/README.md)。本文件只说明后台鉴权与受控审批，不维护当前执行状态；实时状态看 [`AI-HANDOFF.md`](../../AI-HANDOFF.md)。

## 目标

记录后台接口自动化的登录、鉴权和调试规范。后台接口和客户端接口一样使用 CBOR 请求/响应，但登录字段和 header 更敏感，不能只照接口文档裸跑。

## 后台登录规范

后台登录需要两步：

1. `POST {{admin_url}}/admin/login/auth`
2. `POST {{admin_url}}/admin/login`

请求必须满足：

- `content-type` 使用 CBOR runner 时为 `application/cbor`。
- FAT 测试环境后台登录的 `google_code` 当前固定使用 `111111`。
- `google_code` 必须按数字发送，不要按字符串发送。
- `google_secret` 字段需要保留，当前可为空字符串。
- `x-device-id` 需要从浏览器真实请求或环境变量注入。
- `client-id` 当前使用 `123`。
- `client-version` 当前跟随浏览器版本，例如 `Chrome/151.0.0.0`。
- `lang` 当前后台使用 `en`。

不要把真实账号、密码、Google code、token、cookie、设备 id 提交到仓库。

## 环境变量

```bash
ADMIN_URL=https://admin-fat.filbet2025.com
ADMIN_EMAIL=<admin email>
ADMIN_PASSWORD=<admin password>
ADMIN_GOOGLE_CODE=111111
ADMIN_DEVICE_ID=<x-device-id from browser request>
ADMIN_GOOGLE_SECRET=
ADMIN_APPROVAL_TOTP_SECRET=<real approval totp secret>
ADMIN_APPROVAL_TOTP_ALGORITHM=SHA256
ADMIN_LANG_HEADER=en
ADMIN_CLIENT_ID=123
ADMIN_CLIENT_VERSION=Chrome/151.0.0.0
ADMIN_TOKEN_PREFIX=
```

注意：`ADMIN_GOOGLE_CODE` 只用于后台登录。充值补单、提现审核、KYC 审核等管理后台审核动作仍需要真实 Google Authenticator 动态验证码，不能用 `111111` 代替。当前 AI 后台账号二维码使用 SHA256 算法，自动生成审核码时需要设置 `ADMIN_APPROVAL_TOTP_ALGORITHM=SHA256`。

`ADMIN_TOKEN_PREFIX` 默认留空。前端真实请求里的后台业务接口使用裸 token：

```text
t: <admin token>
```

不是：

```text
t: t:<admin token>
```

## 已验证命令

```bash
ADMIN_EMAIL=<admin email> ADMIN_PASSWORD=<admin password> ADMIN_GOOGLE_CODE=111111 ADMIN_DEVICE_ID=<x-device-id> \
python3 scripts/api-smoke-runner.py \
  --admin-login \
  --execute \
  --insecure \
  --body-format cbor \
  --out /tmp/admin-login-cbor.json
```

成功标准：

- `/admin/login/auth`：HTTP 200，业务 `status=true`。
- `/admin/login`：HTTP 200，业务 `status=true`，`data` 为后台 token。

## 已验证后台只读探针

以下接口已在 FAT 调试通过，可作为后台 P0 候选：

| 接口 | 结果 | 断言建议 |
| --- | --- | --- |
| `GET /admin/me/detail` | 通过 | `status_true,data_object` |
| `GET /admin/finance/payment/bank/list` | 通过 | `status_true,data_object,keys:data.d\|data.t\|data.s` |
| `GET /admin/finance/transaction/types` | 通过 | `status_true,data_list` |
| `GET /admin/kyc/pending/count` | 通过 | `status_true` |
| `GET /admin/kyc/config/info` | 通过 | `status_true,data_object` |
| `GET /admin/priv/list?pid=0` | 通过 | `status_true,data_list` |
| `GET /admin/group/list?page=1&page_size=20` | 通过 | `status_true,data_object,keys:data.d\|data.t\|data.s` |
| `POST /admin/kyc/list` | 通过 | `status_true,data_object,keys:data.d\|data.t\|data.s` |
| `POST /admin/finance/deposit/risk/list` | 通过 | `status_true,data_object,keys:data.d\|data.t\|data.s\|data.summary` |
| `POST /admin/finance/withdraw/risk/audit/list` | 通过 | `status_true,data_object,keys:data.d\|data.t\|data.s\|data.summary` |
| `POST /admin/finance/deposit/list` | 通过 | `status_true,data_object,keys:data.d\|data.t\|data.s\|data.summary` |
| `POST /admin/finance/withdraw/list` | 通过 | `status_true,data_object,keys:data.d\|data.t\|data.s\|data.summary` |
| `POST /admin/finance/transaction/list` | 通过 | `status_true,data_object,keys:data.d\|data.t\|data.s` |

当前 FAT 后台测试账号的 `/admin/me/detail` 中 `roles` 可为空字符串，不能以 `roles` 非空作为登录或权限成功标准；权限断言使用 `group_id`、`button_permission_ids` 字段存在，且 `button_permission_ids` 非空，再结合 `/admin/priv/list` 权限树查询。

只执行后台 13 条 safe smoke：

```bash
python3 scripts/api-smoke-runner.py \
  --cases api/p0/test-cases.csv \
  --with-admin-login \
  --base admin \
  --execute --insecure --body-format cbor \
  --out /tmp/admin-p0-smoke.json
```

后台列表 POST 请求不能发送空 body。充值/提现待审列表和财务记录使用 `start_time`、`end_time`、`page`、`page_size`；当前实测为秒级时间戳。`test-cases.csv` 使用动态时间标记，由 smoke runner 在发送前替换。

## 已定位的问题

之前后台 token 失败不是接口不可用，而是 runner 没有完全复刻前端请求：

- 缺少或未注入 `x-device-id`。
- `google_code` 被作为字符串发送，后端期望数字。
- 曾误以为后台接口需要 `t:` 前缀，实际前端业务请求使用裸 token。
- runner 曾把业务失败响应里的字符串误判成 token，现在只在 `status=true` 时提取 token。

## 下一步

后台 P0 接口进入正式用例前，先按以下顺序推进：

1. KYC UI/API 提交后，用 uid/phone 在 `/admin/kyc/list` 定位本次记录，再补详情和通过/驳回的受控 runner。
2. 审批通过、审批拒绝、配置修改、补单、同步状态等接口需要真实审核令牌；只允许操作本次自动化创建的记录，不混入默认只读 smoke。
3. 在 controlled flow 中补齐订单级核对：前后台 uid、订单号、金额、状态、账变方向一致，并检查无重复账变。
4. 后台 safe smoke 可用 `--base admin` 单独执行，便于把后台失败与客户端登录/SMS 环境问题隔离。
