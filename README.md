# FILBET QA Automation

FILBET 的 Python API 与 Playwright UI 自动化项目。API 验证接口契约和订单关联，UI 提供真实页面及三方游戏交互证据。

## 开始使用

需要 Python 3.10+、Node.js/npm；Node 版本应满足锁定的 Playwright 依赖。Python 核心 runner 使用标准库；FAT 数据库诊断另需本地 MySQL 客户端。

```bash
npm ci
npx playwright install chromium
npm run check
```

`check` 仅执行本地资产、文档、语法和单元测试，不登录业务系统。联网执行前根据 [.env.example](.env.example) 准备被 Git 忽略的 `.env.fat` / `.env.uat`，变量及环境差异见 [环境手册](api/runbooks/ENVIRONMENTS.md)。KYC 图片由本地 `KYC_IMAGE` 指定，不提交证件或二维码。

## 日常 P0 测试：两个入口

```bash
# API P0：正例、默认反例及受控写入组合
npm run test:p0:api

# UI P0：默认客户端完整套件
npm run test:ui:p0
```

| 测试 | 实际覆盖范围 |
| --- | --- |
| API P0 | 包含注册、KYC、充值补单、后台清流、提款账户准备、提现及审核阶段；会创建业务数据，不包含真实 UI 投注。已知充值限额缺陷探针不默认执行。 |
| UI P0 | 执行固定 10 条页面与交互用例；专项写入开关关闭时不真实充值、投注或提现。独立 UI 资金专项不包含在这 10 条中。 |

这里的“完整套件”指当前默认可执行范围，不表示所有专项都执行。日常 UI 配置保持 `EXECUTE_BET`、`EXECUTE_DEPOSIT_CONTRACT`、`EXECUTE_WITHDRAW_UI` 为 `false`。

两条命令默认使用 `.env.fat`。切换 UAT 时在对应命令前加 `ENV_FILE=.env.uat`。

## 跑完看哪里

| 内容 | 打开位置 |
| --- | --- |
| API 报告 | [p0-api-report.html](api/results/p0-api-report.html) |
| UI 报告（含过程与截图） | [p0-ui-report.html](ui/reports/p0-ui-report.html) |
| API/P0 用例总索引 | [test-cases.csv](api/p0/test-cases.csv) |
| 默认 UI 用例清单（中文名称） | [client-p0-default-suite.json](ui/data/client-p0-default-suite.json) |
| UI 测试点与正反例设计 | [client-p0-test-points.json](ui/data/client-p0-test-points.json) |

报告在执行后生成，各自保留最近一次结果。日常只需看本页的两个命令及对应报告；组合资金链、单阶段写入和排障参数统一放在 [高级命令说明](docs/commands.md)。

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
- 历史成果：[阶段报告](FILBET-QA阶段成果报告-2026-09-04.md)；CI 验证边界：[CI 状态](docs/ci.md)。

## 结果与业务边界

API 结果及跨 API/UI 主流程报告写入 `api/results/`；UI 原始结果写 `ui/results/`，可读报告写 `ui/reports/`，Playwright 附件写 `test-results/` 和 `playwright-report/`。这些运行目录只保留最近一次结果，历史归档按 CI 状态说明处理；已跟踪的专项扫描快照采用独立保留策略。

每个 runner fresh login，跨进程通过本轮 uid、订单号与时间窗口关联证据。数据库仅只读诊断；业务步骤失败时停止后续成功动作。真实凭据与未脱敏个人资料只留本地忽略配置或 CI 凭据。环境接受标准见 [环境手册](api/runbooks/ENVIRONMENTS.md)，不能把待审建单表述为最终出款成功。
