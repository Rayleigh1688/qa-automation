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
| `api/p0/interface-shortlist.md` | P0 候选摘要 |
| `api/p0/main-flow-scenarios.csv` | P0 主流程正反例场景矩阵 |
| `api/p0/main-flow-scenarios.md` | P0 主流程正反例说明，给功能测试和 AI 共用 |
| `api/runbooks/ADMIN.md` | 后台 API 登录、鉴权、只读探针调试规范 |
| `api/p0/test-cases.csv` | P0 可执行测试用例，runner 直接读取 |
| `api/p0/test-cases.md` | P0 测试用例说明 |
| `api/p0/smoke-report.md` | 最近一次统一 P0 只读 smoke 结论 |
| `api/p0/write-smoke-report.md` | 最近一次 P0 主流程写操作冒烟结论 |
| `api/results/*.json` | 本地原始执行结果，每次覆盖刷新，不提交仓库 |
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
ADMIN_EMAIL=<admin email> ADMIN_PASSWORD=<admin password> ADMIN_GOOGLE_CODE=<google code> ADMIN_DEVICE_ID=<x-device-id> \
python3 scripts/api-controlled-flow-runner.py \
  --main-positive-flow \
  --approval-code <approval code> \
  --insecure \
  --body-format cbor \
  --deposit-amount 10 \
  --withdraw-amount 100 \
  --out api/results/main-positive-flow-result.json
```

注意：后台充值补单当前需要额外验证码，`ADMIN_GOOGLE_CODE` 不一定等于补单验证码。若返回 `invalid verification code`，应抓后台真实补单请求确认字段和值来源。
`scripts/api-controlled-flow-runner.py` 的审批动作优先使用 `--approval-code`，未传时会用本地 `.env` 中的 `ADMIN_APPROVAL_TOTP_SECRET` 动态生成当前验证码。后台登录仍使用 `ADMIN_GOOGLE_CODE`。

生成 Markdown 报告：

```bash
python3 scripts/render-p0-smoke-report.py \
  --result api/results/p0-smoke-result.json \
  --cases api/p0/test-cases.csv \
  --out api/p0/smoke-report.md
```

## 通过标准

每条用例至少满足：

- HTTP 状态为 `200`。
- 响应可解码为 CBOR 或 JSON。
- 业务字段 `status=true`。
- `data` 类型符合用例要求。
- 关键字段存在，例如钱包接口必须包含 `uid`、`balance`、`withdrawable`、`locked`。

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
2. 再读 `api/p0/main-flow-scenarios.csv` 和 `api/p0/test-cases.csv`。
3. 确认环境变量存在，不要把凭据写入仓库。
4. 执行 runner。统一 P0 只读 smoke 默认 30 条，主流程写操作用 `api-controlled-flow-runner.py`。
5. 渲染报告。
6. 如果失败，优先看 `assertion_failures`，再看 `decoded_body`。
7. 不要自动执行 `manual_review` 或 `review_only` 接口。
