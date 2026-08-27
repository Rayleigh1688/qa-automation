# Admin API Runbook

## 目标

记录后台接口自动化的登录、鉴权和调试规范。后台接口和客户端接口一样使用 CBOR 请求/响应，但登录字段和 header 更敏感，不能只照接口文档裸跑。

## 后台登录规范

后台登录需要两步：

1. `POST {{admin_url}}/admin/login/auth`
2. `POST {{admin_url}}/admin/login`

请求必须满足：

- `content-type` 使用 CBOR runner 时为 `application/cbor`。
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
ADMIN_GOOGLE_CODE=<google code>
ADMIN_DEVICE_ID=<x-device-id from browser request>
ADMIN_GOOGLE_SECRET=
ADMIN_LANG_HEADER=en
ADMIN_CLIENT_ID=123
ADMIN_CLIENT_VERSION=Chrome/151.0.0.0
ADMIN_TOKEN_PREFIX=
```

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
ADMIN_EMAIL=<admin email> ADMIN_PASSWORD=<admin password> ADMIN_GOOGLE_CODE=<google code> ADMIN_DEVICE_ID=<x-device-id> \
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

## 已定位的问题

之前后台 token 失败不是接口不可用，而是 runner 没有完全复刻前端请求：

- 缺少或未注入 `x-device-id`。
- `google_code` 被作为字符串发送，后端期望数字。
- 曾误以为后台接口需要 `t:` 前缀，实际前端业务请求使用裸 token。
- runner 曾把业务失败响应里的字符串误判成 token，现在只在 `status=true` 时提取 token。

## 下一步

后台 P0 接口进入正式用例前，先按以下顺序推进：

1. 只纳入只读接口，例如当前用户、报表、列表、配置、待审数量。
2. 审批通过、审批拒绝、配置修改、补单、同步状态等接口继续保持 `do_not_auto_run_yet`。
3. 后台报表类 POST 查询接口需要先确认请求体字段，再用只读断言纳入。
4. 后台接口单独成组执行，避免和客户端 P0 混在同一个最小 smoke 集里造成定位困难。
