# QA Automation

这是一个用于逐步建设测试自动化体系的工作区。

## 目录结构

```text
testing-plan/    测试自动化建设规划
skills/          测试方法、规范、业务规则沉淀
harness/         调试经验、已知问题、失败分析沉淀
api/             API 自动化测试资产
  inventory/     接口文档扫描清单
  p0/            P0 场景、用例等固定资产
  results/       API 最近一次执行结果和报告，已忽略
  runbooks/      API 执行和调试入口文档
ui/              UI 自动化测试
  cases/         Playwright 用例
  elements/      页面对象和操作封装
  framework/     UI 测试基础能力，如环境读取、Network 记录
  data/          UI 测试数据
  reports/       UI 最近一次可读报告
  results/       UI 最近一次原始执行结果，已忽略
performance/     性能测试
scripts/         辅助脚本
```

## 当前状态

当前阶段：P0 核心自动化已形成可执行基线

- P0 只读 smoke：30 条，客户端 25 条 + 后台 5 条。
- P0 API 反例 smoke：14 条默认安全用例，覆盖登录鉴权、KYC 缺字段、旧接口替代、非法参数、无效 token、无效充值通道、低额提现和后台鉴权。
- P0 主流程写操作：注册、充值、后台补单、提现申请、后台提现审核同意和成功标记已形成受控脚本；提现以后台成功记录为验收，不校验第三方到账。
- 客户端 UI 自动化：登录注册、充值、投注、派彩结果链路已跑通；KYC 因业务逻辑和资料准备复杂，第一轮暂时略过。
- UI 定位策略：对难以稳定抓取的三方游戏/canvas 场景，采用固定视口下的 Playwright + 坐标定位组合策略。
- 当前主要风险：客户端自动化账号可能因频繁请求短信被 FAT 限制；CI 需要使用稳定的专用客户端账号或预置 token 策略。充值通道限额后端校验在 FAT 存在已知缺陷，越界契约探针不默认进入 CI。管理后台审核类动作使用已配置的真实 Google Authenticator 动态令牌；后台登录在 FAT 使用固定 `ADMIN_GOOGLE_CODE=111111`。

## 执行规则

- 每次确认规则性问题，都要同步修改对应文档或数据文件，避免只留在对话上下文里。
- 影响测试范围、优先级或执行策略的规则，优先写入 `testing-plan/` 和 `README.md`。
- 影响 P0 接口用例的规则，必须同步更新 `api/p0/main-flow-scenarios.csv`；说明性规则统一写入 `api/p0/README.md`。
- 影响执行方法、账号、令牌、环境变量或调试步骤的规则，写入 `api/runbooks/` 或 `harness/`。
- API 和 UI 自动化结果必须分开：API 结果只写入 `api/results/`；UI 原始结果、截图、trace、视频只写入 `ui/results/`，UI 可读报告写入 `ui/reports/`。
- 测试结果目录只保留最近一次执行产物。每次执行前可以清空旧产物；runner 和报告生成脚本必须使用固定文件名覆盖写入，不做增量追加，不长期保留历史报告。

## AI 参考手册分工

- `README.md`：项目总说明书，记录当前阶段、最高优先级、统一命令、CI 门禁和全局规则。
- `testing-plan/`：测试自动化路线图，记录阶段目标、优先级定义、建设边界和验收标准。
- `api/p0/README.md`：P0 API 固定资产说明，解释 shortlist、main-flow、test-cases 的关系。
- `api/runbooks/`：API 执行手册，记录客户端/后台登录、鉴权、环境变量、受控写操作和调试命令。
- `ui/README.md`：UI 自动化小项目说明，记录 Playwright 目录、执行命令、结果目录和定位策略。
- `harness/`：调试经验和已知问题，记录失败归因、flaky、环境限制、历史坑位；数据库只读字段观察记录在 `harness/database-debug.md`。
- `skills/`：给 AI 的长期操作准则，记录 API/UI 测试方法和业务规则，帮助下一段对话快速接续。
- `api/results/`、`ui/results/`、`ui/reports/`、`playwright-report/`、`test-results/`：仅保存最近一次执行产物，不作为参考手册。

接口新旧版本交替时，版本替代关系维护在 `api/p0/README.md`；具体失败响应和环境现象维护在 `harness/known-errors.md`。

## P0 主流程优先级

当前第一优先级只围绕主流程建设：

1. 登录注册。
2. KYC 查询和状态前置；KYC 提交流程第一轮暂缓。
3. 充值。
4. 投注。
5. 派彩结果和投注/账变数据核对。
6. 提现。
7. 上述行为完成后，管理后台相关数据展示、列表、报表和待审记录查询。

其它功能等这些主流程相关能力稳定通过后再继续扩展。

## P0 自动化执行

统一 API 等级执行：

```bash
python3 scripts/run-api-tests.py p0
```

一次执行多个等级：

```bash
python3 scripts/run-api-tests.py p0 p1
```

P0 包含受控写流程：

```bash
python3 scripts/run-api-tests.py p0 --include-write
```

UI P0：

```bash
npm run test:ui:p0
```

API + UI P0：

```bash
npm run test:p0
```

受控写操作 P0：

```bash
python3 scripts/run-api-tests.py p0 --include-write
```

说明：

- `python3 scripts/run-api-tests.py p0` 执行 P0 正例只读 smoke 和 P0 反例保护性规则，并按 `main-flow-scenarios.csv` 生成主流程报告。
- `python3 scripts/run-api-tests.py p0 p1` 按等级依次执行；当前 P1 资产不存在时会跳过并提示。
- `--include-write` 用于受控主流程调试，包含注册、充值、后台补单、提现申请、后台提现审核同意和标记成功；提现以后台成功记录为验收，不校验项目外收款账户或真实到账，只应在测试环境或专用 UAT 测试数据下执行。
- `test:ui:p0` 默认不执行真实投注。需要点击三方游戏内投注区域时，必须显式设置 `EXECUTE_BET=true`。
- 后台登录固定码和审核动态码是两套东西：`ADMIN_GOOGLE_CODE=111111` 只用于 FAT 后台登录，审核/补单/KYC 审批使用 `ADMIN_APPROVAL_TOTP_SECRET` 生成真实动态码。
- API 执行会覆盖 `api/results/` 下同名结果和报告；UI 执行会覆盖 `ui/results/` 和 `ui/reports/` 下同名产物。需要历史记录时，以 CI 归档为准，不在仓库工作区内累积。
- 需要单独清空生成物时，执行 `python3 scripts/clean-test-artifacts.py all`；只清 API 或 UI 时分别用 `api`、`ui` 参数。
- FAT 主流程正例当前使用稳定充值通道 Gcash `pid=47870534954254469`、金额 `50`；充值/补单账号和提现账号必须拆开，避免充值补单产生的流水影响提现。
- 本地或 CI 推荐通过 `WRITE_CLIENT_PHONE`、`WRITE_CLIENT_OTP` 注入受控写/充值账号，通过 `WITHDRAW_CLIENT_PHONE`、`WITHDRAW_CLIENT_OTP` 注入专用提现账号；也可以在命令中传 `--write-client-phone`、`--write-client-otp`、`--withdraw-client-phone`、`--withdraw-client-otp`。

## CI 门禁

Jenkinsfile 已支持参数化执行：

| 参数 | 推荐值 | 用途 |
| --- | --- | --- |
| `TARGET_ENV` | `fat` / `uat` | `fat` 用于发布 UAT 前测试环境验证，`uat` 用于发布 UAT 后验证 |
| `P0_SCOPE` | `api_all` | 执行 API 正例 P0 + API 反例 P0 |
| `EXECUTE_BET` | `false` | 默认不做真实投注点击 |

推荐发布流程：

1. 发布 UAT 前，在测试环境执行：`TARGET_ENV=fat`、`P0_SCOPE=api_all`。
2. 发布 UAT 后，在 UAT 执行：`TARGET_ENV=uat`、`P0_SCOPE=api_all`。
3. UI 自动化作为补充检查，需要确认前端页面或三方游戏链路时再执行 `P0_SCOPE=api_ui` 或 `ui_only`。
4. 涉及充值、提现、审核链路专项验证时，人工触发 `P0_SCOPE=api_write`，并确认测试账号、活动流水、审核令牌和资金影响可控。

CI 需要通过 Jenkins 环境变量或凭据注入：

```bash
FAT_API_URL=https://client-fat.filbet2025.com
FAT_ADMIN_URL=https://admin-fat.filbet2025.com
FAT_CLIENT_BASE_URL=https://client-fat.filbet2025.com
UAT_API_URL=<uat client api url>
UAT_ADMIN_URL=<uat admin url>
UAT_CLIENT_BASE_URL=<uat client url>
CLIENT_PHONE=<client phone>
CLIENT_OTP=<otp>
WRITE_CLIENT_PHONE=<controlled write/deposit client phone>
WRITE_CLIENT_OTP=<otp>
WITHDRAW_CLIENT_PHONE=<dedicated withdraw client phone>
WITHDRAW_CLIENT_OTP=<otp>
ADMIN_EMAIL=<admin email>
ADMIN_PASSWORD=<admin password>
ADMIN_DEVICE_ID=<x-device-id>
ADMIN_GOOGLE_CODE=111111
ADMIN_APPROVAL_TOTP_SECRET=<approval totp secret>
ADMIN_APPROVAL_TOTP_ALGORITHM=SHA256
```

CI 归档产物：

- `api/p0/README.md`
- `api/results/*.md`
- `api/results/*.json`
- `ui/reports/*.md`
- `ui/results/**/*.json`
- `ui/results/screenshots/**/*`
- `playwright-report/**/*`
- `test-results/**/*`

## UI 自动化

首次使用：

```bash
npm install
npx playwright install
```

配置本地 `.env`：

```bash
CLIENT_BASE_URL=https://client-fat.filbet2025.com
CLIENT_PHONE=<client phone>
CLIENT_OTP=<fat otp>
PLAYWRIGHT_CHANNEL=
```

常用命令：

```bash
npm run test:ui:p0
npm run test:ui:p0:scan
npm run test:ui:p0:pn
npm run test:ui:inventory
npm run test:ui:login
npm run test:ui:game-bet
npm run ui:p0-points
```

- `npm run test:ui:p0`：执行客户端 P0 UI 默认套件，包含登录正反例、主流程扫描、游戏启动冒烟、页面状态正反例；默认不做真实资金动作。
- `npm run test:ui:p0:scan`：只执行 Playwright P0 客户端主流程扫描用例。
- `npm run test:ui:p0:pn`：只执行客户端 P0 UI 正反例补充用例。
- `npm run test:ui:inventory`：按 `ui/data/client-pages.json` 扫描客户端页面定位资产，输出 `ui/reports/client-locator-inventory.md`。
- `npm run test:ui:login`：执行客户端登录正反例。
- `npm run test:ui:game-bet`：登录后进入配置的游戏页；默认只验证启动，设置 `EXECUTE_BET=true` 才点击游戏内投注区域。
- `npm run ui:p0-points`：根据 `ui/data/client-p0-test-points.json` 生成客户端 P0 UI 测试点报告。
- UI 原始 JSON、截图、视频索引在 `ui/results/`，默认不提交 Git。
- `PLAYWRIGHT_CHANNEL` 默认留空，使用 Playwright 自带 Chromium；需要指定本机 Chrome 时再设置为 `chrome`。

## 使用原则

- 先完善规划，再分阶段落地。
- 先做 P0 核心链路，再扩展 P1、P2。
- API P0 资产放在 `api/p0/`；UI 用例、配置、报告分别放在 `ui/cases/`、`ui/data/`、`ui/reports/`。
- `api/results/`、`ui/results/`、`ui/reports/`、`playwright-report/`、`test-results/` 都是可再生成产物目录，只保留最近一次结果。
- 敏感信息不提交到 Git。
- 测试账号、Token、Cookie、环境变量使用本地配置或 CI 凭据管理。
