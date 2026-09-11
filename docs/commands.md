# 高级命令与执行范围

日常 API P0、默认 UI 页面回归和 FAT UI 业务全流程，直接使用 [README 的三个入口](../README.md#日常-p0-测试三个入口)。按测试目的选择，共用账号或结果目录时串行执行。本文件供参数调整、组合资金链、专项和排障时查阅。

这里维护公开命令的语义；具体参数由 `package.json` 与脚本定义，环境契约见 [环境手册](../api/runbooks/ENVIRONMENTS.md)。

| 命令 | 执行范围 | 业务写入与证据边界 |
| --- | --- | --- |
| `python3 scripts/run-requirement-api.py ISOP-2032` | 需求API数据与Case引用离线校验 | 不联网；多个需求用空格分隔。增加`--env .env.fat --execute --insecure`执行白名单查询及鉴权/参数反例，按需求留存独立结果；无配置/审批/发奖/导出任务写入 |
| `npm run check` | 资产、文档、源码语法和本地单元测试 | 无业务请求 |
| `npm run test:p0:api:read` | safe API + 默认保护性反例 | 有认证请求，不创建资金订单；不包含已知会建单的充值限额探针 |
| `npm run test:ui:p0` | 固定默认 UI 清单 | 默认只验证页面/游戏启动；专项写入开关应保持关闭 |
| `ENV_FILE=.env.fat npm run test:ui:kyc` | 独立 FAT KYC UI 提交，`--approve` 衔接本轮后台审核和浏览器刷新 | 会上传/提交测试资料；不进入默认 10 条，不执行资金链；账号或业务失败即停 |
| `npm run test:ui:business -- --env .env.fat` | 默认只读资金前置；`--execute` 执行 KYC UI、UI 充值、3–5 笔付费 UI 投注、显式后台清流、UI 提现和对账 | 同资金号串行；API 只补单/审核及查询，禁止 API 建单代替 UI；详见 UI 手册 |
| `npm run test:ui:business:fat` | 固定 `.env.ui-p0.fat` 的完整 UI 受控写入映射：新 KYC、充值 1200、3 笔各 100、清流、提现 1000、对账 | 启用 `--execute --new-kyc-account --bet-spins 3 --clear-remaining-turnover --allow-existing-turnover --headed`，明确包含专用资金号遗留流水清零；不是只读检查 |
| `npm run test:p0` | safe API/negative + 默认 UI | 快速组合门禁 |
| `npm run test:p0:api` | safe/negative + 新号注册、KYC、充值补单、后台清流、提款账户准备、提现及审核阶段 | 会写业务数据；纯 API，不证明三方投注；遇业务失败停止，不能保证最终出款 |
| `npm run test:p0:full` | 永久 BASIC UI 拦截、独立 KYC、safe/negative、默认 UI、充值、真实 UI 投注、流水及提现关联 | 会写业务数据；默认按剩余流水投注；后台清流由 `--clear-remaining-turnover` 显式启用 |

`test:api`、`test:api:write` 与 `test:p0:api` 调用同一个 API 入口；`test:p0:ui` 是默认 UI 别名。不要把 `test:api` 当成只读命令。

所有业务 npm 与清理入口现由本机锁包装；原业务命令与参数不变，直接 CLI 的保护方式见 [团队本地运行](local-running.md)。`npm run doctor` 默认只做本地准备检查，`--network` 显式开启无认证 HTTPS 探测；`--target business` 增加受控 UI 依赖检查。`QA_ENV_LOCAL` 显式选择个人覆盖文件。

## 环境和参数

```bash
ENV_FILE=.env.fat npm run test:p0:api:read
ENV_FILE=.env.uat npm run test:ui:p0
python3 scripts/run-api-tests.py p0 --env .env.uat --scope UAT --safe-only
```

完整链路固定次数示例（包含资金写入）：

```bash
ENV_FILE=.env.fat npm run test:p0:full -- --bet-spins 10 --clear-remaining-turnover --deposit-amount 1200 --withdraw-amount 1000
```

Python UI/full 入口支持 `--headed`。固定次数模式分别记录投注后流水与后台清流后流水，不能声称流水全由投注完成。

单阶段注册、KYC、充值、提现、查询和审批命令见 [API 手册](../api/runbooks/API.md) 和 [P0 资产说明](../api/p0/README.md)；UI 专项开关见 [UI 手册](../ui/README.md)。查询/审批必须关联当前 flow 的明确 ID。

## 结果语义

- API 报告统计请求/断言，UI 报告统计固定用例，主流程报告统计八个业务场景，数量不能直接比较。
- 结构查询允许空页时，仅证明响应契约；订单关联必须证明本轮订单存在且字段匹配。
- `test:p0:api` 生成 API 报告；完整主流程报告由 `test:p0:full` 负责。
- 非零退出表示运行没有通过。既有 runner 的 `FAILED/BLOCKED` 表达不同失败阶段，诊断时同时查看阶段、退出码及原始错误。

## API / UI 可复制命令（FAT）

API 无资金写入（认证与默认保护性反例仍会发送请求）：

```bash
ENV_FILE=.env.fat npm run test:p0:api:read
```

API 受控写入组合（注册、KYC、充值补单、后台清流、账户准备、提现及审核阶段，不含真实 UI 投注）：

```bash
ENV_FILE=.env.fat npm run test:p0:api
```

UI 默认套件，明确关闭资金开关；`ENV_FILE_PRECEDENCE=shell` 防止本地配置覆盖显式开关：

```bash
ENV_FILE=.env.fat ENV_FILE_PRECEDENCE=shell EXECUTE_BET=false EXECUTE_DEPOSIT_CONTRACT=false EXECUTE_WITHDRAW_UI=false npm run test:ui:p0
```

下列为三个原有独立 UI 写动作专项；自动串联的新入口是 `npm run test:ui:business -- --env .env.fat --execute --clear-remaining-turnover`（前置和受限续跑见 UI 手册）：

```bash
# 充值页面创建订单 1000，不等于后台补单或实际到账
ENV_FILE=.env.fat ENV_FILE_PRECEDENCE=shell EXECUTE_DEPOSIT_CONTRACT=true CLIENT_DEPOSIT_AMOUNT=1000 npm run test:ui:deposit-contract

# 游戏内真实投注 1 次；单注读取本地 CLIENT_GAME_BET_AMOUNT
ENV_FILE=.env.fat ENV_FILE_PRECEDENCE=shell EXECUTE_BET=true CLIENT_GAME_SPIN_COUNT=1 npm run test:ui:game-bet

# Maya 提现页面提交 1000；需已 KYC、余额/流水/提款账户满足前置及本地 CLIENT_WALLET_PASSWORD
ENV_FILE=.env.fat ENV_FILE_PRECEDENCE=shell EXECUTE_WITHDRAW_UI=true CLIENT_WITHDRAW_CHANNEL=Maya CLIENT_WITHDRAW_AMOUNT=1000 npm run test:ui:withdraw-contract
```

默认 10 条 UI 不提交提现；提现专项明确开启写开关才提交合法订单。以上专项各自清理 UI 最近结果，且不自动调用默认 UI 汇总渲染器；不能把专项结果当成默认 10 条套件已重跑。完整跨 API/UI 资金链使用本文件的 `test:p0:full`，其中提现由 API 创建。

`python3 scripts/render-ui-business-report.py` 仅用当前证据重建 UI 业务报告及断言明细，不执行测试或业务请求。受控 UI 新运行会清理上一轮 UI 报告/图片，续跑保留本轮检查点，详见 [UI 报告与覆盖规则](../ui/README.md#业务报告断言与产物覆盖)。

## Telegram 提测

`npm run qa:telegram` 只扫描并输出requirements目录内的需求级待确认列表，不执行测试。`npm run qa:telegram -- preview`只读本地队列刷新清单，不扫描或调用AI。确认后用 `run --requirements ISOP-2022,ISOP-2032 --revision ...` 按需求选择；同需求多个批次须用兼容的`--candidates`明确选择。每个Story固定一名负责人；报告和候选留本机，用 `approve --job ... --revision ... --bugs B1,B2` 确认具体产品BUG，再用 `submit` 创建并关联，整批成功后才一次性发群清单。`check` 离线检查；`verify` 只读核对Telegram和Jira连接。无常驻监听，详见 [Telegram接入手册](telegram-qa.md)。

## CSV用例与结果树

`npm run qa:report -- --cases <cases.csv>`仅离线校验用例；同时提供`--results <recorded-results.json> --out <新目录>`生成结果树和CSV，不登录、不执行业务。报告生成成功不代表测试通过。格式与迁移范围见[统一流程](testing-workflow.md)。

## 新需求统一执行入口（ISOP-2027试点）

`python3 scripts/run-requirement.py ISOP-2027`默认离线校验；`--export-cases`从plan.json生成CSV；`--only <id...>`、`--layer API`选择范围；`--rebuild <run目录>`离线重建到新视图目录。实施与验证见[阶段记录](new-requirement-stage1-2.md)。旧run-requirement-api.py与P0入口保持兼容。

`npm run qa:requirement -- ISOP-2027 --env .env.fat --execute --insecure --allow-write kyc-review --allow-write kyc-permissions`按当前策略执行FAT自动分配计划（默认排除人工分配的UI/FLOW；显式选择可运行旧UI脚本），注册/KYC/编辑/复核仅作用于本轮独立会员；权限步骤仅对B独占的当前Codex角色撤权并finally恢复。省略`--execute`不登录；省略所需写范围在前置校验阶段拒绝。BUG和群投递不在此命令中。可加`--version <发布标识>`写入声明版本，默认未提供；`--expected-plan-sha256 <hash>`拒绝计划变化，`--result-index <新文件>`供编排方获取本次完成结果，不读latest挑选证据。

新入口执行退出码：0为所选用例全部PASS，1为存在FAIL/ERROR，2为没有FAIL/ERROR但仍有NOT_RUN（包括无最大长度契约的观察）。离线校验/重建退出0仅代表该离线操作成功。

固定UI使用`--layer UI`；双账号三图UI核准/驳回使用`--only 2027-FLOW-003 2027-FLOW-004`，均需`--execute --insecure --allow-write kyc-review`。页面资产、会话与实测边界见[阶段3记录](new-requirement-stage3.md)。

## 团队执行包与回填

`npm run qa:delivery -- prepare <Story> --environment FAT --out <新目录>`离线生成API自动表与人工清单；`import --packet <执行包> --manual <回填CSV> --out <新报告目录>`导入人工结果，可重复提供`--auto-results <原始结果JSON>`。细节见[团队流程](team-testing.md)。ISOP-2027默认qa:requirement执行自动分配项；`--include-ui-automation`恢复包含既有UI脚本的范围，`--only/--layer UI`仍可显式选择。

## 报告精简与清理

`qa:requirement`（执行和`--rebuild`）、`qa:delivery prepare/import`默认只导出results.csv/results.html；加`--extra-views`才额外导出cases/failures/pending CSV和summary.json。原始结果、快照、必要证据及团队API/人工表继续保留；旧qa:report、查询CLI、P0的路径和产物契约不变。

`check:archive`名称保留，现检查旧扫描目录只留退出索引，不再读取已删除的manifest。2026-09-11一次性全项目清理见[整理记录](project-cleanup-2026-09-11.md)；未增加自动删除运行历史的任务。现有P0清理命令仍只处理原API/UI生成目录，不清理Telegram状态或新需求包。

## 分离总用例与API数据

`npm run qa:cases -- <Story...>`离线导出指定需求的cases.csv总表，以及已有执行资产的api/data-cases.csv；`--all`导出全部需求。总表来自test-cases.md，API表来自plan.json或旧api/cases.json，不登录、不生成运行结果。没有API执行源的需求只导出总表，命令明确显示API未实现。

原`qa:requirement -- <Story> --export-cases`同步生成这两类表并继续更新旧查询兼容JSON。总表使用业务Case ID，数据表和`--only`使用执行Case ID；总表ID不直接传给`--only`。详细执行结果用本批冻结快照重建，不能与业务总表按执行编号直接合并。已有团队执行包不自动重写。

当前执行策略（2026-09-11）：P0继续运行并维护API与核心UI自动化；新需求使用API自动执行与UI人工回填，暂不建设新需求UI自动化。本文保留的专项UI参数只说明兼容能力，不表示应自动续跑新需求UI或停止P0 UI。


`qa:telegram run`对有plan.json的需求使用统一API执行器，按已确认计划hash/用例选择执行；UI生成team-packet/manual.csv供人工执行，不启动新需求浏览器。`npm run qa:telegram -- import-manual --job <job> --revision <当前报告版本> --manual <本批回填CSV>`合并明确API来源和人工结果、重新评审BUG，不重跑业务、不建单或发群；导入后使用新revision确认BUG。写范围和未迁移需求兼容规则见[Telegram流程](telegram-qa.md#测试与证据边界)。
