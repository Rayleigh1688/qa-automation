# P0 API AI Runbook

## 目标

这套资产用于让任意 AI 代理或自动化执行器在不依赖对话上下文的情况下，完成 P0 API 冒烟验证。

当前 P0 覆盖范围：

- 客户端只读 P0：登录前置、KYC、充值/提现资料、投注、钱包、账变、会员、VIP、代理资料。
- 后台只读 P0：后台登录前置、当前用户、银行卡、账变类型、KYC 待审数量、eKYC 配置。
- 主流程写操作 P0：新增测试用户、创建充值订单、提现申请调试。

## 资产入口

| 文件 | 用途 |
| --- | --- |
| `api/inventory/interfaces.csv` | Bruno 全量接口资产清单，包含原始 URL、清洗 URL、标记、P0 候选 |
| `api/inventory/interfaces.md` | 接口资产摘要 |
| `api/p0/interface-shortlist.csv` | P0 候选接口清单 |
| `api/p0/main-flow-scenarios.csv` | P0 主流程正反例场景矩阵 |
| `api/p0/README.md` | P0 API 资产说明和执行规则 |
| `api/runbooks/ADMIN.md` | 后台 API 登录、鉴权、只读探针调试规范 |
| `api/p0/test-cases.csv` | P0 可执行测试用例，runner 直接读取 |
| `api/results/*.json` | 本地原始执行结果，每次覆盖刷新，不提交仓库 |
| `api/results/*.md` | 本地 Markdown 执行报告，每次覆盖刷新，不提交仓库 |
| `scripts/run-api-tests.py` | 按等级统一执行 API 测试的入口 |
| `scripts/clean-test-artifacts.py` | 清空 API/UI 生成物目录，只保留 `.gitkeep` |
| `scripts/api-smoke-runner.py` | 登录、请求、CBOR 编解码、断言执行器 |
| `scripts/render-p0-smoke-report.py` | 将 JSON 执行结果渲染为 Markdown 报告 |

## 环境变量

不要把真实凭据提交到 Git。用本地 shell、`.env` 或 CI secret 注入：

```bash
API_URL=https://client-fat.filbet2025.com
CLIENT_PHONE=<client phone>
CLIENT_OTP=<otp code>
DEVICE=25
LANG_HEADER=en_US
```

后台登录已经验证可用，后台接口登录规范见 `api/runbooks/ADMIN.md`。

## 执行命令

推荐按等级统一执行：

```bash
python3 scripts/run-api-tests.py p0
python3 scripts/run-api-tests.py p0 p1
python3 scripts/run-api-tests.py p0 --include-write
```

统一入口会在执行前清空 `api/results/`，然后覆盖写入本次结果。需要只清理生成物时执行：

```bash
python3 scripts/clean-test-artifacts.py api
python3 scripts/clean-test-artifacts.py all
```

FAT 测试环境当前需要临时跳过本机 TLS 证书校验：

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

如果只需要快速跑客户端前 25 条，可以临时使用 `--limit 25` 且只传 `--with-client-login`。这只是执行策略，不代表后台 P0 被拆成另一套资产。

P0 主流程写操作冒烟：

```bash
CLIENT_PHONE=<client phone> CLIENT_OTP=<otp code> REGISTER_OTP=<otp code> \
python3 scripts/api-controlled-flow-runner.py \
  --register \
  --deposit \
  --withdraw \
  --insecure \
  --body-format cbor \
  --out api/results/controlled-write-result.json
```

P0 主流程正向调试，包含客户端登录、钱包前后检查、充值下单、后台登录、充值补单尝试、提现申请、提现审核列表：

```bash
CLIENT_PHONE=<client phone> CLIENT_OTP=<otp code> \
ADMIN_EMAIL=<admin email> ADMIN_PASSWORD=<admin password> ADMIN_GOOGLE_CODE=111111 ADMIN_DEVICE_ID=<x-device-id> \
python3 scripts/api-controlled-flow-runner.py \
  --main-positive-flow \
  --client-phone <controlled write/deposit phone> \
  --withdraw-client-phone <withdraw dedicated phone> \
  --insecure \
  --body-format cbor \
  --deposit-pid 47870534954254469 \
  --deposit-amount 50 \
  --withdraw-amount 1000 \
  --out api/results/main-positive-flow-result.json
```

注意：FAT 后台登录的 `ADMIN_GOOGLE_CODE` 固定为 `111111`。管理后台审核动作需要真实 Google Authenticator 动态验证码，充值补单、提现审核、KYC 审核等都不能用 `111111`。如果使用 `ADMIN_APPROVAL_TOTP_SECRET` 自动生成审核码，需要按二维码参数设置 `ADMIN_APPROVAL_TOTP_ALGORITHM`，当前 AI 后台账号为 `SHA256`。
`scripts/api-controlled-flow-runner.py` 的审批动作优先使用 `--approval-code`，未传时会用本地 `.env` 中的 `ADMIN_APPROVAL_TOTP_SECRET` 动态生成当前验证码。

当前 FAT 正例经验：

- 充值正例优先使用 Gcash 通道 `pid=47870534954254469`，金额 `50`。COINS 通道曾返回 `Failed to load payment channels, please contact customer service!`，不适合作为稳定主流程正例。
- 充值补单会给当前客户端账号产生新的流水/锁定金额，因此提现正例不要复用同一个客户端账号。
- 提现正例使用已 KYC、无未完成流水、已绑定提款账户的专用账号，金额建议大于 `500`。主流程随后在 FAT/UAT 后台审核同意并标记成功，验收以后台成功记录为准，不校验项目外账户或真实到账。
- `scripts/run-api-tests.py p0 --include-write` 默认使用 GCash `pid=47870534954254469`、充值金额 `50`、提现金额 `1000`；受控写/充值账号用 `WRITE_CLIENT_PHONE`/`WRITE_CLIENT_OTP` 或 `--write-client-phone`/`--write-client-otp` 注入，专用提现账号用 `WITHDRAW_CLIENT_PHONE`/`WITHDRAW_CLIENT_OTP` 或命令行参数注入。
- `--main-positive-flow` 默认创建提现单、查询待审列表、审核同意并标记成功；不会访问第三方出款渠道。仍需要真实审核动态码。单独调试时，可用 `--approve-withdraw --withdraw-mark-success` 显式执行相同步骤。
- 默认只读客户端账号如果返回 `This mobile number has been restricted`，说明测试环境短信触发限频；不要直接判定主流程失败，先切到 `WRITE_CLIENT_PHONE` 或更换专用只读账号。
- 只读 smoke 账号必须是成熟账号：能登录、已绑定提款账户，最好已 KYC。新注册零余额账号可用于充值写流程，但不适合作为完整 P0 smoke 账号。
- 提现账号会被成功创建的提现单持续消耗可提现余额；如果出现 `Insufficient balance`，需要通过接口补资或切换提现账号池，不要直接改库。

生成 Markdown 报告：

```bash
python3 scripts/render-p0-smoke-report.py \
  --result api/results/p0-smoke-result.json \
  --cases api/p0/test-cases.csv \
  --out api/results/p0-smoke-report.md
```

## 通过标准

每条用例至少满足：

- HTTP 状态为 `200`。
- 响应可解码为 CBOR 或 JSON。
- 业务字段 `status=true`。
- `data` 类型符合用例要求。
- 关键字段存在，例如钱包接口必须包含 `uid`、`balance`、`withdrawable`、`locked`。

数据库只读权限不是 P0 API 默认执行前置。只有在确认状态枚举、字段含义、账号前置或落库一致性时才使用；CI 门禁仍以 API 和后台只读接口断言为准。

## 用例排序原则

`api/p0/test-cases.csv` 按玩家业务流程排序，方便 AI 和人类阅读：

1. 注册登录：由 runner 作为前置动作完成，不作为普通 CSV 用例。
2. KYC。
3. 充值。
4. 投注。
5. 派彩/投注相关数据检查。
6. 提现。
7. 以上相关数据检查。
8. 后台报表展示和审批。

底层执行器可以按依赖关系、登录态和安全策略调整实际请求顺序，但报告和用例资产以业务流程为主。

## 场景设计原则

`api/p0/main-flow-scenarios.csv` 是上层场景资产，用来沉淀主流程正反例。新增接口进入可执行 P0 前，先判断它属于哪个场景：

- 注册登录：OTP、token、三方登录、验证码规则、鉴权失败。
- KYC：查询、提交校验、重复提交、状态限制。
- 充值：渠道、下单、金额边界、通道不可用、记录检查。
- 投注：新版游戏列表、旧接口替代、非法参数、维护游戏。
- 派彩：投注记录、派彩记录、账变核对。
- 提现：提现配置、提现申请、余额/KYC/资金密码限制、记录检查。
- 相关数据检查：钱包、账变、会员、VIP、活动配置。
- 后台：报表展示、审批列表和详情、权限、审批动作跳过。

写接口自动化时，不能只根据接口文档生成用例。接口文档负责发现接口，主流程场景负责决定测试价值和正反例边界。

## 写操作边界

注册、充值、提现属于 P0 主流程写操作冒烟，不放入只读 smoke，是为了避免每次快速门禁都创建订单或触发资金冻结。

以下接口类型仍默认不自动执行：

- 支付回调。
- 创建、更新、删除后台配置。
- KYC 提交、审核、驳回。
- 领取奖励、签到、补签。
- 后台配置修改。
- 任何依赖真实资金、审核流、第三方回调或不可自动回滚的数据写操作。

## 已知替代关系

| 老接口 | 状态 | 替代接口 |
| --- | --- | --- |
| `GET /member/game/list` | HTTP 200 但业务 `status=false` | `GET /member/v2/index`、`GET /member/game/listRw`、`GET /member/game/list/recommend` |
| `GET /member/vip` | HTTP 200 但业务失败 | `GET /promo/vip/config`、`GET /promo/vip/sign/in/config` |

## 给 AI 的操作顺序

1. 先读本文件。
2. 再读 `api/p0/README.md`、`api/p0/main-flow-scenarios.csv` 和 `api/p0/test-cases.csv`。
3. 确认环境变量存在，不要把凭据写入仓库。
4. 优先执行 `python3 scripts/run-api-tests.py p0`。需要受控写流程时加 `--include-write`。
5. 渲染报告。
6. 如果失败，优先看 `assertion_failures`，再看 `decoded_body`。
7. 不要自动执行 `manual_review` 或 `review_only` 接口。
