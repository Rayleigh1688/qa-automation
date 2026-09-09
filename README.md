# FILBET QA Automation

FILBET 的 Python API 与 Playwright UI 自动化项目。API 验证接口契约和订单关联，UI 提供真实页面及三方游戏交互证据。

## 开始使用

需要 Python 3.10+、Node.js/npm；Node 版本应满足锁定的 Playwright 依赖。Python 核心 runner 使用标准库；FAT 数据库诊断另需本地 MySQL 客户端。

先按 [本地手册的虚拟环境与 Windows 步骤](docs/local-running.md#python-虚拟环境与-windows) 创建并选择本机 `.venv`；不要跨电脑复制虚拟环境。Windows 已有组员跑通反馈；本次重构后的平台验证边界见同一手册。

```bash
npm ci
npx playwright install chromium
npm run check
```

`check` 仅执行本地资产、文档、语法和单元测试，不登录业务系统。联网执行前按 [团队本地运行手册](docs/local-running.md) 从统一的 FAT/UAT 模板准备被 Git 忽略的配置；用 `QA_ENV_LOCAL` 叠加个人账号，先运行 `npm run doctor -- --env .env.fat`（默认离线）。变量及环境差异见 [环境手册](api/runbooks/ENVIRONMENTS.md)。KYC 图片由本地 `KYC_IMAGE` 指定，不提交证件或二维码。

## 日常 P0 测试：三个入口

```bash
# API P0：正例、默认反例及受控写入组合
npm run test:p0:api

# UI P0：默认页面与交互回归（不含完整KYC/充值/提现流程）
npm run test:ui:p0

# FAT UI 业务全流程：KYC、充值、3 笔投注、清流、提现及对账（真实写入）
npm run test:ui:business:fat
```

| 测试 | 实际覆盖范围 |
| --- | --- |
| API P0 | 包含注册、KYC、充值补单、后台清流、提款账户准备、提现及审核阶段；会创建业务数据，不包含真实 UI 投注。已知充值限额缺陷探针不默认执行。 |
| UI P0 | 执行固定 10 条页面与交互用例；专项写入开关关闭时不真实充值、投注或提现。独立 UI 资金专项不包含在这 10 条中。 |
| FAT UI 业务全流程 | 独立 KYC UI、充值 1200、3 笔各 100 的付费投注、后台清流（含专用资金号遗留流水）、UI 提现 1000 待审及前后台对账；打开可见浏览器，结束后自动关闭。 |

默认 UI 是页面回归；KYC 上传与提交、充值下单、真实投注和提现提交由下面的独立 UI 业务入口执行。`npm run test:p0:full` 仍是 API+UI 混合资金链，KYC、充值及提现主要由 API 执行，不能替代 UI 业务验证。默认页面回归配置保持 `EXECUTE_BET`、`EXECUTE_DEPOSIT_CONTRACT`、`EXECUTE_WITHDRAW_UI` 为 `false`。

API P0 与默认 UI P0 使用 `.env.fat`，切换 UAT 时在对应命令前加 `ENV_FILE=.env.uat`。UI 业务全流程固定使用 `.env.ui-p0.fat`，仅支持 FAT。三个入口按测试目的独立选择；npm 入口以本机锁串行保护运行与清理，后一次 UI 测试会覆盖前一次 UI 产物。KYC 每轮新号、BASIC 永久未认证、资金号按执行者分配；本地锁不提供跨机器账号保护，详见 [本地手册](docs/local-running.md)。

## UI 业务全流程：一条命令

完成环境配置后，可独立运行，无需 AI 或人工看图。当前该入口仅支持 FAT；除上述依赖外，还需 ImageMagick 7（`magick`）和 Tesseract 英文识别。将 FAT 服务、分离的 KYC/BASIC/资金账号、本地 KYC 素材及真实审批 TOTP 配置在 Git 忽略的 `.env.ui-p0.fat` 中；资金账号须已通过 KYC、绑定有效提款账户并配置钱包密码。配置及账号要求见 [环境手册](api/runbooks/ENVIRONMENTS.md) 和 [UI 执行手册](ui/README.md#固定付费投注与显式清流独立执行)。

```bash
npm run test:ui:business -- --env .env.ui-p0.fat --execute --new-kyc-account --bet-spins 3 --clear-remaining-turnover --headed
```

日常入口 `test:ui:business:fat` 固定使用 `.env.ui-p0.fat`、新 KYC 账号、3 笔付费投注、后台清流及可见浏览器，等价于上述完整命令额外加 `--allow-existing-turnover`，**显式纳入专用资金号的遗留流水清零**。需要调整参数或无窗口执行时使用原 `test:ui:business` 入口。

该命令会创建测试业务数据，依次执行：独立新号的 UI KYC 上传/提交及后台审核、刷新页面确认状态 → 资金账号 UI 充值 1200 及后台补单到账 → UI 完成 3 笔已结算付费投注（每笔 100）→ 后台清零剩余流水 → 客户端 UI 提现 1000 → 前后台订单、账变和余额对账。新 KYC 号通过 API 准备，不算 UI 注册证据；提现验收为成功提交且订单待审，不代表最终出款。

`--bet-spins` 可配置 3–5 笔；普通投注最小间隔 2 秒，每次还须确认新增付费注单。免费旋转/忙碌时每 5 秒检查一次，最多等待 60 秒恢复，超时停止。默认要求资金号无遗留流水；确需将专用测试号旧流水纳入清零时，额外传 `--allow-existing-turnover`。`--headed` 打开可见浏览器，自动化环境可省略。

任何阶段失败都会停止后续业务动作并以非零状态退出，不能用 API 成功代替 UI 通过。每轮生成含逐步断言和图片证据的业务报告，并覆盖旧 UI 报告、截图、视频和 trace；同轮受控续跑保留必要证据。续跑限制及图片未采集等状态见 [UI 手册](ui/README.md)。

## 跑完看哪里

| 内容 | 打开位置 |
| --- | --- |
| API 报告 | [p0-api-report.html](api/results/p0-api-report.html) |
| UI 报告（含过程与截图） | [p0-ui-report.html](ui/reports/p0-ui-report.html) |
| UI 业务全流程报告（断言、图片及对账） | [ui-business-report.html](ui/reports/ui-business-report.html) |
| API/P0 用例总索引 | [test-cases.csv](api/p0/test-cases.csv) |
| 默认 UI 用例清单（中文名称） | [client-p0-default-suite.json](ui/data/client-p0-default-suite.json) |
| UI 测试点与正反例设计 | [client-p0-test-points.json](ui/data/client-p0-test-points.json) |

报告在执行后生成，运行目录保留最近一次结果；UI 业务新一轮会清理旧 UI 产物。日常回归与受控业务全流程按上述不同入口执行；组合资金链、单阶段写入和排障参数统一放在 [高级命令说明](docs/commands.md)。

## 接下来：新需求测试

新需求从 [测试设计入口](requirements/README.md) 开始，使用需求模板关联验收标准、API/UI 用例和现有 P0。低频低风险接口随需求迭代补充；已有扫描只作 [历史参考](archive/interface-scans/README.md)。

## 项目结构

| 目录 | 职责 |
| --- | --- |
| `api/p0/` | 场景、完整用例索引、账号 lane 等固定资产 |
| `api/inventory/`、`api/catalog/` | 接口发现源与生成的分类视图 |
| `api/runbooks/` | API 执行、后台鉴权、环境契约 |
| `ui/cases/`、`ui/elements/` | Playwright 编排与页面操作 |
| `ui/data/`、`ui/framework/` | 页面资产、固定套件和基础能力 |
| `scripts/` | 兼容 CLI 入口及单元测试；`qa_core/` 存放共享 API 基础能力 |
| `tools/provisioning/` | 独立账号准备工具 |
| `.agents/skills/`、`skills/` | AI 任务路由及长期测试方法 |
| `harness/` | 故障定位与有状态的已知问题记录 |
| `testing-plan/` | 阶段目标与验收规划 |
| `archive/interface-scans/` | 各端扫描历史资产，统一索引与校验清单 |
| `requirements/` | 按新需求组织测试设计、验收映射和结论 |
| `docs/` | 命令、架构、CI 状态和历史交接 |

详细依赖与维护边界见 [架构说明](docs/architecture.md)。

## 阅读入口

- 接手当前工作：[AI-HANDOFF.md](AI-HANDOFF.md)。
- 修改仓库：[AGENTS.md](AGENTS.md)；业务任务由 [FILBET Skill](.agents/skills/filbet-p0-automation/SKILL.md) 按需路由。
- API 资产：[P0 说明](api/p0/README.md)；UI 执行：[UI 说明](ui/README.md)。
- 排障：[Harness](harness/README.md)；专项快照：[接口发现](archive/interface-scans/README.md)。
- 历史成果：[冻结交接](docs/history/handoff-2026-09-04.md)；CI 验证边界：[CI 状态](docs/ci.md)。

## 结果与业务边界

API 结果及跨 API/UI 主流程报告写入 `api/results/`；UI 原始结果写 `ui/results/`，可读报告写 `ui/reports/`，Playwright 附件写 `test-results/` 和 `playwright-report/`。这些运行目录只保留最近一次结果，历史归档按 CI 状态说明处理；已跟踪的专项扫描快照采用独立保留策略。

每个 runner fresh login，跨进程通过本轮 uid、订单号与时间窗口关联证据。数据库仅只读诊断；业务步骤失败时停止后续成功动作。真实凭据与未脱敏个人资料只留本地忽略配置或 CI 凭据。环境接受标准见 [环境手册](api/runbooks/ENVIRONMENTS.md)，不能把待审建单表述为最终出款成功。

新项目复用公共运行能力，见 [跨项目运行核心](docs/runtime-reuse.md)：包含白名单导出、独立接入示例与 Windows/Mac/Linux 验证边界。
