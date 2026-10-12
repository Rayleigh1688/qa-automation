# Test Data Provisioning

本目录保存脱离 P0 门禁主流程的测试数据准备工具，例如创建会员、初始化 KYC/资金状态，以及后续创建代理。它们不是测试用例，不进入默认 API/UI/CI 命令。

## 边界

- 默认只允许只读发现和 dry-run；写操作必须显式传 `--execute`。
- 所有业务请求继续复用 `scripts/` 中已经验证的 CBOR、登录、TOTP、KYC 和财务实现，不在工具目录复制协议栈。
- 只允许在 FAT/UAT 等测试环境使用；工具拒绝明显的生产环境 URL。
- 注册、KYC 审批和充值补单必须使用同一个本次新建会员；任何阶段业务失败立即停止。
- 原始账号、UID、token、订单和响应只写入 Git 忽略的 `api/results/provisioning/`，不得写入文档或提交 Git。
- 默认创建流程只把账号推进到“注册成功、KYC 已通过、充值已补单”的检查点。提款账户使用独立的显式准备步骤；投注、流水归零和提现仍由 P0 主流程处理。

## 创建已 KYC 且已充值的会员

先只读查找未注册号码并生成计划：

```bash
python3 tools/provisioning/member-bootstrap.py --env .env.uat
```

确认计划后显式执行完整初始化：

```bash
python3 tools/provisioning/member-bootstrap.py \
  --env .env.uat \
  --execute \
  --deposit-amount 1200 \
  --kyc-image 21000000008072.webp
```

起始手机号优先读取 `--start-phone`，其次读取 `REGISTER_PHONE`、`PROVISION_PHONE_START`，然后读取环境专属本地游标；都没有时默认从 `9000000001` 开始。工具不依赖数据库：先用已知会员验证管理后台 `POST /admin/member/list` 的手机号精确筛选确实生效，再逐号递增查询，返回第一个不存在的会员。FAT/UAT 游标分别保存在 Git 忽略的 `api/local-state/register-phone-<environment>.json`，不会被 API 报告清理器删除；游标保存本次候选，下次先复查该号码，确认已注册才继续加一。

接口发现需要为不同写操作准备独立会员时，可停在注册或 KYC 审核完成阶段，并为每个 lane 使用独立的 ignored 输出目录，避免不必要的充值及证据覆盖：

```bash
python3 tools/provisioning/member-bootstrap.py \
  --env .env.fat \
  --execute \
  --stop-after register \
  --out-dir api/results/provisioning/interface-discovery/member-state-lane
```

`--stop-after kyc` 会完成注册、KYC 提交和后台审核后停止；默认 `--stop-after deposit` 保持原来的完整初始化行为。无论在哪一阶段停止，原始手机号、UID、session 和响应仍只保存在指定的 ignored 目录。

UAT 动态验证码使用：

```dotenv
CLIENT_OTP_SOURCE=admin_sms
REGISTER_OTP_SOURCE=admin_sms
```

`member-bootstrap.py` 执行完成后，汇总文件为 `api/results/provisioning/member-bootstrap-summary.json`。阶段原始结果和 session 也在同一忽略目录中。

## 代理下的多人资金样本

批量准备先固定测试环境、代理集合、每组人数、每名充值目标及整批上限，再只读核现有直属、推荐码、余额、KYC和订单。已有直属可在用户指定的本批范围内复用；只补不足人数，不重复注册或转线。手机号下一起点同时参考环境游标和本批已使用最大号码，UID始终按十进制字符串关联。

逐会员完成KYC并确认客户端状态为5后，再执行充值；待审记录按精确UID核对。充值使用当前通道范围合法的金额，后台补单前核客户端订单与后台内部ID、会员、代理、金额和外单号，不能以待审列表第一行代替。补单后核完成状态、钱包准确增量和累计充值；不以后台上分替代充值指标。

每次写入前保存尝试边界，成功回执立即保存身份／订单。业务失败即停资金链，只读核是否实际落单或到账，不重放创建或对失败请求调用成功接口。身份／KYC准备与资金阶段可分别留存结果，未到账的清单明确标为待充值，不交付为可投注资金号。账号与密码清单只放在本机忽略目录；交给用户投注后避免同时重新登录这些会员。

客户端通道的金额范围与支付商户的实际限制分开判断；通道显示允许大额，不证明商户配置也允许。用户确认商户限制已修复或取得新的配置证据后，先fresh只读核前次失败确实无订单、无到账，再以独立资金批次继续已授权目标，保留原失败。已有账号和KYC只复核；不能覆盖旧日志、对前次业务失败的订单补成功或在未核后态时重复建单。最终交付核前后台完成单、单会员累计、准确钱包增量、每组直属集合和整批金额上限，并更新原账号清单链接及投注前基线。

当前5组各3名会员使用已有可导入能力进行定向编排，结果与阻断见[10-09代理准备](../../modules/agency/preparation-20261009.md)。此批尚无通用批量npm／CLI入口，不扩展默认P0或CI。

## 为已创建会员准备 Maya 提款账户

该步骤先检查会员详情：没有钱包密码时调用 `/finance/wallet/pwd/set` 设置本地配置的统一密码，已有密码时不覆盖；随后验证密码并查询已有提款账户。相同 Maya 账号已存在或本地已有成功证据时不会重复创建。

```bash
python3 tools/provisioning/member-bootstrap.py \
  --env .env.uat \
  --prepare-withdrawal \
  --execute \
  --wallet-password '<6-digit wallet password>' \
  --maya-account '<Maya account>' \
  --maya-pid '<UAT Maya channel pid>'
```

也可以通过忽略的环境变量 `CLIENT_WALLET_PASSWORD`、`PROVISION_MAYA_ACCOUNT` 和 `PROVISION_MAYA_PID` 注入，不要把真实值写入仓库。

如果会员已经由人工绑定提款账户，不要再执行本步骤；刷新 session 后通过 `/finance/account/list` 只读复核即可。同一账号在别处重新登录会使已保存的客户端 token 失效，工具遇到失效 session 会停止，不会为了继续绑定而自动登录并挤掉当前浏览器会话。

## 为新会员设置登录密码

该步骤封装当前前端的两段式接口：先用 `/member/auth/sms` 验证当次短信，再用 `/member/retrieve/password` 设置密码。两步均使用 CBOR 请求体和前端实际的 JSON content-type；第一步失败时不会调用第二步。

```bash
python3 tools/provisioning/member-bootstrap.py \
  --env .env.uat \
  --set-login-password \
  --execute \
  --login-password '<8-20 chars, letter + number>' \
  --login-password-otp-id '<current otp id>' \
  --login-password-code '<current 6-digit code>'
```

也可由忽略的 `PROVISION_LOGIN_PASSWORD`、`PROVISION_LOGIN_PASSWORD_OTP_ID` 和 `PROVISION_LOGIN_PASSWORD_CODE` 注入。验证码和 otp id 必须属于同一次短信，结果文件不会保存验证码或密码。会员详情已经显示 `has_login_password=true` 时整步跳过，避免覆盖已有密码。

如果业务写入已经执行、但汇总校验中断，只复核已有本地证据，不重放注册、KYC 或充值：

```bash
python3 tools/provisioning/member-bootstrap.py \
  --env .env.uat \
  --validate-existing \
  --deposit-amount 1200
```

充值完成检查以“创建订单与后台成功处理订单一致、钱包总余额增量等于本次充值额”为准；后台待处理列表是否及时返回该行作为辅助证据记录，不单独决定失败。

纯工具逻辑测试不访问环境：

```bash
npm run test:unit
```
