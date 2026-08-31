# P0 API AI Runbook

上级入口：[`api/p0/README.md`](../p0/README.md)。涉及后台登录、权限或审批时继续阅读 [`ADMIN.md`](ADMIN.md)；出现环境或响应异常时从 [`harness/README.md`](../../harness/README.md) 选择排障分支。

## 目标

这套资产用于让任意 AI 代理或自动化执行器在不依赖对话上下文的情况下，完成 P0 API 冒烟验证。

当前 P0 覆盖范围：

- 客户端只读 P0：登录前置、KYC、充值/提现资料、投注、钱包、账变、会员、VIP、代理资料。
- 后台只读 P0：后台登录前置、当前用户、银行卡、账变类型、KYC 待审数量、eKYC 配置。
- 主流程受控写 P0：新增测试用户、充值下单和后台补单、提现申请及后台审核同意/成功标记。

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
| `api/results/*.html` | 本地静态可视化报告，每次覆盖刷新，不提交仓库 |
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
python3 scripts/run-api-tests.py p0 --safe-only
```

统一入口会在执行前清空 `api/results/`，然后覆盖写入本次结果。需要只清理生成物时执行：

```bash
python3 scripts/clean-test-artifacts.py api
python3 scripts/clean-test-artifacts.py all
```

统一入口会额外生成 `api/results/p0-api-report.html`。这是不依赖服务端的单文件静态报告：首屏显示 `PASS`、`PARTIAL` 或 `BLOCKED`，并按主流程分组展开场景的接口、前置条件、断言和运行结论。

FAT 测试环境当前需要临时跳过本机 TLS 证书校验：

```bash
CLIENT_PHONE=<client phone> CLIENT_OTP=<otp code> \
ADMIN_EMAIL=<admin email> ADMIN_PASSWORD=<admin password> ADMIN_GOOGLE_CODE=<google code> ADMIN_DEVICE_ID=<x-device-id> \
python3 scripts/api-smoke-runner.py \
  --cases api/p0/test-cases.csv \
  --with-client-login \
  --with-admin-login \
  --limit 0 \
  --execute \
  --insecure \
  --body-format cbor \
  --out api/results/p0-smoke-result.json
```

完整 safe smoke 使用 `--limit 0`，runner 会按 `test-cases.csv` 的 `case_order` 执行全部 31 条 `safe_smoke`。需要只跑客户端或后台时分别使用 `--base client`、`--base admin`，不要再用数字 limit 表示某个业务范围。

P0 主流程写操作冒烟：

```bash
CLIENT_PHONE=<client phone> CLIENT_OTP=<otp code> REGISTER_OTP=<otp code> \
python3 scripts/api-controlled-flow-runner.py \
  --register \
  --register-phone <allocated 090XXXXXXXX KYC phone> \
  --deposit \
  --withdraw \
  --insecure \
  --body-format cbor \
  --out api/results/controlled-write-result.json
```

P0 资金主流程阶段 B 调试，只执行客户端登录、充值下单、后台补单和钱包检查：

```bash
CLIENT_PHONE=<client phone> CLIENT_OTP=<otp code> \
ADMIN_EMAIL=<admin email> ADMIN_PASSWORD=<admin password> ADMIN_GOOGLE_CODE=111111 ADMIN_DEVICE_ID=<x-device-id> \
python3 scripts/api-controlled-flow-runner.py \
  --deposit \
  --approve-deposit \
  --client-phone <fund flow phone> \
  --insecure \
  --body-format cbor \
  --deposit-pid 47870534954254469 \
  --deposit-amount 1200 \
  --out api/results/fund-flow-seed-result.json
```

P0 KYC 新号提交专项（受控写；三项附件可复用同一张测试图片）：

```bash
CLIENT_PHONE=<new 090XXXXXXXX phone> CLIENT_OTP=111111 \
python3 scripts/api-controlled-flow-runner.py \
  --submit-kyc \
  --client-phone <new 090XXXXXXXX phone> \
  --client-otp 111111 \
  --kyc-image 21000000008072.webp \
  --kyc-first-name Codex \
  --kyc-middle-name '-' \
  --kyc-last-name 001 \
  --kyc-birthday 1993-08-31 \
  --kyc-gender male \
  --kyc-nationality Philippines \
  --kyc-place-of-birth Manila \
  --kyc-current-address Manila \
  --kyc-permanent-address Manila \
  --kyc-nearest-branch '2040 Taft Ave, Pasay, Metro Mani' \
  --kyc-nature-of-work 'Employed – Permanent/Contractual' \
  --kyc-source-of-income 'Employment Income' \
  --kyc-id-type COUNTRY_ID \
  --insecure \
  --body-format cbor \
  --out api/results/kyc-submit-result.json
```

runner 会按当前客户端契约依次查询 KYC 前置和动态分行、上传三项附件、调用 `/member/kyc/insert`，再查询提交后详情。KYC 手机号由登录账号自动带出，不能在表单中覆盖；成功提交只代表进入 `Under Review`，不会自动执行后台通过或驳回。

注意：FAT 后台登录的 `ADMIN_GOOGLE_CODE` 固定为 `111111`。管理后台审核动作需要真实 Google Authenticator 动态验证码，充值补单、提现审核、KYC 审核等都不能用 `111111`。如果使用 `ADMIN_APPROVAL_TOTP_SECRET` 自动生成审核码，需要按二维码参数设置 `ADMIN_APPROVAL_TOTP_ALGORITHM`，当前 AI 后台账号为 `SHA256`。
`scripts/api-controlled-flow-runner.py` 的审批动作优先使用 `--approval-code`，未传时会用本地 `.env` 中的 `ADMIN_APPROVAL_TOTP_SECRET` 动态生成当前验证码。

当前 FAT 正例经验：

- 充值正例优先使用 Gcash 通道 `pid=47870534954254469`。当前同账号资金主流程使用金额 1200；COINS 通道曾返回 `Failed to load payment channels, please contact customer service!`，不适合作为稳定主流程正例。
- 注册不再临时生成手机号。执行完整写流程必须通过 `REGISTER_PHONE` 或 `--register-phone` 指定已分配的 `090XXXXXXXX` KYC 测试池账号，避免生成无法追踪、无法继续 KYC 的孤立账号。
- 充值补单产生的流水/锁定金额属于主流程验证目标。同一个 `fund_flow_account` 必须先经过真实投注和流水轮询，再发起提现。
- `scripts/run-api-tests.py p0` 默认执行到充值与补单检查点并停止。建议资金参数为充值 `1200`、首次 UI 投注 `1000`、提现探针 `1000`；跨 API、UI 和数据库的放行规则见 `api/p0/README.md`。
- `--main-positive-flow` 仅保留为兼容别名，现在也会停在充值检查点。提现和后台审核仅可在流水检查点通过后用显式 `--withdraw --check-admin-withdraw-list --approve-withdraw --withdraw-mark-success` 执行。
- 默认只读客户端账号如果返回 `This mobile number has been restricted`，说明测试环境短信触发限频；不要直接判定主流程失败，先切到 `WRITE_CLIENT_PHONE` 或更换专用只读账号。
- 只读 smoke 账号必须是成熟账号：能登录、已绑定提款账户，最好已 KYC。新注册零余额账号可用于充值写流程，但不适合作为完整 P0 smoke 账号。
- 提现账号会被成功创建的提现单持续消耗可提现余额；如果出现 `Insufficient balance`，需要通过接口补资或切换提现账号池，不要直接改库。
- 测试账号池规则维护在 `api/p0/test-account-pool.csv`。KYC 新账号优先使用 `090XXXXXXXX`，从 `09000000001` 开始；测试环境登录 OTP 固定为 `111111`。
- `9888888050` 当前已知存在提现流水限制，不作为提现正例默认账号；可切换无流水限制的提现账号，或由后台解除该账号流水限制后再复验。
- 充值页面的 `Multiple Deposit Bonus` 活动开关默认关闭/不参加。参加活动会产生提现流水限制；做无流水限制提现验证前必须确认该开关未开启，或明确接受该账号后续不能直接提现。

生成 Markdown 报告：

```bash
python3 scripts/render-p0-smoke-report.py \
  --result api/results/p0-smoke-result.json \
  --cases api/p0/test-cases.csv \
  --out api/results/p0-smoke-report.md
```

## 通过标准

正例用例至少满足：

- HTTP 状态为 `200`。
- 响应可解码为 CBOR 或 JSON。
- 业务字段 `status=true`。
- `data` 类型符合用例要求。
- 关键字段存在，例如钱包接口必须包含 `uid`、`balance`、`withdrawable`、`locked`。

反例用例以场景断言为准：必须得到预期的业务拒绝或安全降级，不能只因 HTTP `200` 或 `status=false` 自动判通过；写操作反例还要验证没有产生不应有的订单、冻结或状态变化。

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

`api/p0/main-flow-scenarios.csv` 只维护 8 条端到端主流程；正反例明细统一维护在 `test-cases.csv`。新增接口进入可执行 P0 前，先判断它属于哪个主流程：

- 注册登录：OTP、token、三方登录、验证码规则、鉴权失败。
- KYC：查询、提交校验、重复提交、状态限制。
- 充值：渠道、活动配置、可购买免费旋转配置、下单、金额边界、通道不可用、记录检查。
- 投注：新版游戏列表、投注旋转活动、旧接口替代、非法参数、维护游戏。
- 派彩：投注记录、派彩记录、账变核对。
- 提现：提现配置、提现申请、余额/KYC/资金密码限制、记录检查。
- 相关数据检查：钱包、账变、会员、VIP、弹窗、活动配置、Filcoin。
- 后台：报表展示、审批列表和详情、权限，以及本次专用测试单的受控审批动作。

写接口自动化时，不能只根据接口文档生成用例或决定顺序。接口文档只负责发现；真实客户端 Network 决定当前版本路径，业务状态依赖决定访问顺序，`test-cases.csv` 决定正反例和账号 lane。

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
4. 优先执行 `python3 scripts/run-api-tests.py p0`，它默认覆盖当前受控读写主流程；只读诊断时加 `--safe-only`。
5. 渲染报告。
6. 如果失败，优先看 `assertion_failures`，再看 `decoded_body`。
7. 不要自动执行 `manual_review` 或 `review_only` 接口。
