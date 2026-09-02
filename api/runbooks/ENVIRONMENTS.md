# FAT / UAT 环境差异

本文件是 FAT 与 UAT 执行差异的唯一规则来源。这里只记录非敏感规则和环境变量名；账号、密码、OTP、TOTP seed、token、设备号等真实值只允许存在于忽略的 `.env.fat`、`.env.uat` 或 CI 凭据中。

## 环境矩阵

| 维度 | FAT（测试环境） | UAT |
|---|---|---|
| 环境文件 | `.env.fat` | `.env.uat` |
| 客户端/后台 URL | 读取 `API_URL`、`CLIENT_BASE_URL`、`ADMIN_URL` | 同一组变量，值必须全部指向 UAT，禁止混用 FAT URL |
| 既有客户端账号登录 | UI/API 默认密码登录 | UI/API 默认密码登录 |
| 新账号注册 | `REGISTER_PHONE` 使用 FAT 账号池；固定 OTP 可用 | 从指定 UAT 号段顺序寻找未注册号码；通过后台短信查看接口在内存取动态 OTP |
| 后台登录码 | 登录阶段可使用环境配置的固定码 | 使用当前管理账号的动态 TOTP |
| 审批动态码 | KYC、补单、提现审批均使用 `ADMIN_APPROVAL_TOTP_SECRET` | 同样使用真实审批 TOTP；登录码不能替代审批码 |
| TOTP 算法 | 当前配置为 SHA256 | 当前已验证管理账号为 SHA256 |
| CBOR | 客户端和后台业务接口均按 CBOR 契约执行 | 同样使用 CBOR；部分前端请求虽然 body 为 CBOR，`Content-Type` 实际仍为 `application/json`，runner 按接口契约覆盖 |
| TLS | 当前本地 runner 默认允许 `--insecure` | 只在确有证书链需要时使用，不能把跳过校验当成业务规则 |
| 资金账号 | 使用 FAT 专用 `fund_flow_account` | 使用本次自动创建、已 KYC、已充值、已设置钱包密码并绑定 Maya 的账号 |
| 永久未 KYC 账号 | `PRE_KYC_CLIENT_PHONE` 永久保持 BASIC | 同样使用独立永久 BASIC 账号，不得提交 KYC 或设置钱包密码 |
| 游戏 | FAT 保留现有 Jili 游戏配置 | BNG `Coins`，游戏页由 `CLIENT_GAME_PAGE_PATH` 配置 |
| 业务单注 | `CLIENT_GAME_BET_AMOUNT=1000` | `CLIENT_GAME_BET_AMOUNT=100`（UAT 当前最大投注额） |
| 提现通道 | Maya 为稳定建单通道；真实出款受 FAT 转账接口配置限制 | Maya 已绑定；使用同一资金账号继续提现链路 |
| 已确认异常 | 充值限额未校验、偶发 502、短信限制、无可用转账接口 | 提款账户列表曾单次返回 `status=true,data=null`，后续连续复核恢复 |

## 账号与凭据变量

环境文件使用同一套 schema：

- 只读账号：`CLIENT_PHONE`、`CLIENT_PASSWORD`；`CLIENT_AUTH_MODE=password` 为两套环境默认值。
- 资金账号：`WRITE_CLIENT_PHONE`、`WRITE_CLIENT_PASSWORD`；BET/WITHDRAW 为兼容别名。
- 新注册账号：`REGISTER_PHONE`、`REGISTER_PASSWORD`、`REGISTER_OTP_SOURCE`。
- 永久未 KYC 账号：`PRE_KYC_CLIENT_PHONE`、`PRE_KYC_CLIENT_PASSWORD`。
- 钱包密码：`CLIENT_WALLET_PASSWORD`。
- 后台登录与审批：`ADMIN_EMAIL`、`ADMIN_PASSWORD`、`ADMIN_LOGIN_TOTP_SECRET`、`ADMIN_APPROVAL_TOTP_SECRET`。

同一环境内登录密码和钱包密码采用统一测试约定，但真实值不得写入本文档或其他受版本控制文件。

### 账号 lane 差异

- FAT 新账号使用既有 `090XXXXXXXX` 测试池规则。
- UAT 新账号从指定 `900000000X` 号段开始，先通过 `POST /admin/member/list` 精确确认不存在，再由 controlled flow 注册。
- UAT 资金账号应注册满 7 天、KYC 已通过、无遗留流水；余额可以由主链充值，但必须配置钱包密码和提款账户。
- 永久未 KYC lane 应注册满 30 天、KYC 未提交、无钱包密码和提现历史；选定后永久禁止提交 KYC 或设置钱包密码。
- 后台筛选只能证明候选状态；最终仍需客户端登录并复核 `/finance/account/list` 及 safe smoke。

## 执行规则

```bash
# FAT safe gate
python3 scripts/run-api-tests.py p0 --env .env.fat --scope FAT --safe-only

# UAT safe gate
python3 scripts/run-api-tests.py p0 --env .env.uat --scope UAT --safe-only

# UAT UI
ENV_FILE=.env.uat npm run test:ui:p0
```

- 命令必须显式选择环境；报告中的 scope 与环境文件必须一致。
- API 既有账号默认调用 `POST /member/v2/login`。只有注册、首次设密以及显式设置 `CLIENT_AUTH_MODE=otp` 的专项才请求短信验证码。
- `.env.example` 只定义变量 schema，不保存任何环境真实值。
- 环境异常和失败证据记录到 `harness/known-errors.md`，本文件只保留仍然有效的差异结论。
- 当前执行实现与目标规则不一致时，在 `AI-HANDOFF.md` 记录下一步，不提前把未实现行为写成已完成。
