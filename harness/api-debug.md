# API Debug

## 用途

记录 API 自动化测试调试方法。

## 调试记录

## 基本流程

1. 先确认接口属于客户端、后台还是代理后台。
2. 先看 `api/inventory/interfaces.csv` 和 `api/p0/interface-shortlist.csv`。
3. 再看是否已有场景映射：
   - P0 用例：`api/p0/test-cases.csv`
   - 主流程：`api/p0/main-flow-scenarios.csv`
4. 用 runner 做最小探针，先只断言 `status_true`。
5. 通过后再补充 `data_object`、`data_list`、`keys:...` 等稳定断言。
6. 失败时先看 `decoded_body`，不要只看 HTTP 状态。

## 客户端调试

客户端登录：

```bash
CLIENT_PHONE=<client phone> CLIENT_OTP=<otp code> \
python3 scripts/api-smoke-runner.py \
  --client-login \
  --execute \
  --insecure \
  --body-format cbor \
  --out /tmp/client-login.json
```

执行统一 P0 只读 smoke：

```bash
CLIENT_PHONE=<client phone> CLIENT_OTP=<otp code> \
ADMIN_EMAIL=<admin email> ADMIN_PASSWORD=<admin password> ADMIN_GOOGLE_CODE=<google code> ADMIN_DEVICE_ID=<x-device-id> \
python3 scripts/api-smoke-runner.py \
  --cases api/p0/test-cases.csv \
  --with-client-login \
  --with-admin-login \
  --limit 30 \
  --execute \
  --insecure \
  --body-format cbor \
  --out api/results/p0-smoke-result.json
```

## 后台调试

后台登录必须复刻前端请求关键字段：

- `x-device-id` 从浏览器真实请求获取，通过 `ADMIN_DEVICE_ID` 注入。
- `google_code` 按数字发送。
- `google_secret` 字段保留，当前可为空。
- `lang=en`。
- `client-id=123`。
- token 裸值放入 `t` header。

快速只跑客户端前 25 条时，可以只传 `--with-client-login --limit 25`。这只是执行提速，不是拆分 P0 资产。

后台登录探针：

```bash
ADMIN_EMAIL=<admin email> ADMIN_PASSWORD=<admin password> ADMIN_GOOGLE_CODE=<google code> ADMIN_DEVICE_ID=<x-device-id> \
python3 scripts/api-smoke-runner.py \
  --admin-login \
  --execute \
  --insecure \
  --body-format cbor \
  --out /tmp/admin-login.json
```

## 报告刷新

结果 JSON 和报告 MD 都是覆盖刷新，只保留最近一次执行产物。执行前允许清空 `api/results/`；API runner 必须写固定文件名，不按时间戳或次数累积新文件：

- `api/results/p0-smoke-result.json`
- `api/results/p0-smoke-report.md`
- `api/results/p0-negative-result.json`
- `api/results/p0-negative-report.md`
- `api/results/p0-main-flow-report.md`
- `api/results/controlled-write-result.json`
- `api/results/main-positive-flow-result.json`

原始 JSON 和 Markdown 报告都不提交，最近一次结论以当前工作区生成物为准；历史记录交给 CI 归档系统。

## P0 主流程写操作冒烟

注册、充值、提现属于 P0 主流程。它们不进入只读 P0 门禁，但使用独立 runner 执行：

```bash
CLIENT_PHONE=<client phone> CLIENT_OTP=<otp code> \
python3 scripts/api-controlled-flow-runner.py \
  --deposit \
  --withdraw \
  --insecure \
  --body-format cbor \
  --out api/results/controlled-write-result.json
```

注册探针：

```bash
REGISTER_PHONE=<new test phone> REGISTER_OTP=<otp code> \
python3 scripts/api-controlled-flow-runner.py \
  --register \
  --insecure \
  --body-format cbor \
  --out api/results/controlled-write-result.json
```

`api/results/controlled-write-result.json` 每次覆盖刷新，且不提交仓库。
