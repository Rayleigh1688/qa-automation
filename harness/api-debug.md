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

定位客户端子集时可以临时使用 `--limit`。这只是执行提速，不是拆分 P0 资产；完整 P0 不设置该参数，避免新增 safe smoke 后被静默截断。

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

## 数据库只读权限边界

API 主流程自动化默认不依赖数据库读取权限。优先通过客户端 API、后台只读 API 和受控写 runner 完成前置、执行和断言。

数据库只读权限适合用于：

- 对照 KYC、充值、提现、投注、账变等状态枚举和字段含义。
- 确认后台列表/详情字段与落库字段的映射关系。
- 排查 API 返回为空或状态不符合预期时，是数据前置问题、环境问题还是业务逻辑问题。
- 为专用测试账号矩阵确认账号状态，例如已 KYC、未 KYC、低余额、无活动流水限制、有投注账变数据。

数据库只读权限不应成为默认门禁依赖；CI 默认仍以 API 返回和后台只读接口为准。

## 报告刷新

结果 JSON 和报告 MD 都是覆盖刷新，只保留最近一次执行产物。执行前允许清空 `api/results/`；API runner 必须写固定文件名，不按时间戳或次数累积新文件：

- `api/results/p0-smoke-result.json`
- `api/results/p0-smoke-report.md`
- `api/results/p0-negative-result.json`
- `api/results/p0-negative-report.md`
- `api/results/p0-main-flow-report.md`
- `api/results/p0-api-report.html`
- `api/results/controlled-write-result.json`
- `api/results/fund-flow-seed-result.json`

原始 JSON 和 Markdown 报告都不提交，最近一次结论以当前工作区生成物为准；历史记录交给 CI 归档系统。

## 单阶段受控写调试

日常完整执行使用 `python3 scripts/run-api-tests.py p0`。只有定位单一写阶段时才直接运行底层 runner；不要把下面命令当作常规入口。

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

## 主流程正例调试结论

- 充值下单和提现申请都已通过接口正例探针跑通。
- 充值通道从当前环境的 `mode=1` 列表动态选择；当前资金主流程金额为 1200，环境间不得复用通道 PID。
- COINS 通道 `pid=55278060248820714` 曾返回 `Failed to load payment channels, please contact customer service!`，不要作为当前稳定正例通道。
- 提现金额 `100` 会低于免审阈值 `500`，可能自动出款后失败，接口最终返回 `Service is busy, please try again later！`，但数据库中可看到提现单和账变先发生再冲回。
- 资金主流程使用同一个已 KYC、已绑定提款账户的 `fund_flow_account`：充值补单后必须完成真实投注并等待流水统计，再测试限制和正向提现。
- `CLIENT_PHONE` 仍用于只读 smoke；`WRITE_CLIENT_PHONE` 为资金主流程账号，BET/WITHDRAW 兼容变量可指向同一账号。
- FAT 默认客户端手机号可能因为频繁请求短信返回 `This mobile number has been restricted. Please contact customer support.`；出现该错误时优先更换只读或写流程专用账号，不要直接判定接口链路失败。
- 新注册零余额账号可以登录和充值，但没有提款账户时 `/finance/account/list` 可能返回 `data=null`，不能作为完整 P0 只读 smoke 账号。
- 提现会消耗可提现余额；余额不足时 `/finance/payment/withdraw` 返回 `Insufficient balance`。不能把该结果误判为已经命中流水限制文案。
