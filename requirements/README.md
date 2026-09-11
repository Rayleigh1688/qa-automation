# 新需求 AI 自动化测试设计

日常 P0 回归入口仍在 [README](../README.md)。这里按需求组织设计与执行证据，不要求先覆盖全部接口，也不因新需求自动扩展 P0。

新需求执行能力当前按[API/UI完善计划](../docs/new-requirement-automation-plan.md)分阶段推进；ISOP-2027阶段1、2及固定UI阶段3已交付，证据与剩余事项见[API记录](../docs/new-requirement-stage1-2.md)和[UI记录](../docs/new-requirement-stage3.md)。用户查看以自动生成的`results.csv`/`results.html`为主，保留用例、预期、实际与通过/失败；普通用例逐步迁移为结构化执行数据，尚未迁移的历史资产不视为已可一键重跑。

2026-09-11新交付接口已按顺序开测，中文报告、实际失败和未执行范围见[本轮结果](api-test-round-20260911.md)。

## 需求索引与组织约定

按 Jira 编号建立 `requirements/<Jira编号>/`，不再按年/月套目录。同一需求的补充、复测与重新打开继续维护原目录；新的 Jira 需求建新目录并链接相关需求。日期、来源版本和执行批次记录在文档中。

需求索引按创建时间倒序，新需求在上、老需求在下；后续新增需求按此顺序插入。完成的需求保留原目录及索引位置，完成状态以需求文档中的验收结论为准，不从排序推断。单个需求内的验收点、问题及用例按编号正序，便于引用和执行。

本轮选取依据、跨需求依赖和建议分工见 [批次评审](review-summary.md)。

群消息扫描的待确认任务以这里已有需求目录的工单为单位，子任务提测归并到所属需求；无提测记录不因目录存在而列入。终端显示简洁需求列表，详细依据保存在本地preview.json；查看与选择命令见[Telegram流程](../docs/telegram-qa.md#手动扫描一次)。

| Jira 编号 | 需求名称 | 分离文档 |
| --- | --- | --- |
| ISOP-2072 | 報表數據更改爲排程計算 | [设计](ISOP-2072/design.md) · [问题](ISOP-2072/questions.md) · [总用例](ISOP-2072/cases.csv) · [用例设计](ISOP-2072/test-cases.md) |
| ISOP-2070 | Funky 時間回傳問題 | [设计](ISOP-2070/design.md) · [问题](ISOP-2070/questions.md) · [总用例](ISOP-2070/cases.csv) · [用例设计](ISOP-2070/test-cases.md) |
| ISOP-2043 | 管理後台 - 新增 JP 資訊 | [设计](ISOP-2043/design.md) · [问题](ISOP-2043/questions.md) · [总用例](ISOP-2043/cases.csv) · [用例设计](ISOP-2043/test-cases.md) · [API数据](ISOP-2043/api/data-cases.csv) |
| ISOP-2041 | JP 注單寫入方式調整 | [设计](ISOP-2041/design.md) · [问题](ISOP-2041/questions.md) · [总用例](ISOP-2041/cases.csv) · [用例设计](ISOP-2041/test-cases.md) |
| ISOP-2038 | 合規後台 - 移除 Jackpot 記錄選單 | [设计](ISOP-2038/design.md) · [问题](ISOP-2038/questions.md) · [总用例](ISOP-2038/cases.csv) · [用例设计](ISOP-2038/test-cases.md) |
| ISOP-2037 | 合規後台 - 全平台投注紀錄增加欄位 | [设计](ISOP-2037/design.md) · [问题](ISOP-2037/questions.md) · [总用例](ISOP-2037/cases.csv) · [用例设计](ISOP-2037/test-cases.md) · [API数据](ISOP-2037/api/data-cases.csv) |
| ISOP-2032 | 用戶端 - 投注返利活動 | [设计](ISOP-2032/design.md) · [问题](ISOP-2032/questions.md) · [总用例](ISOP-2032/cases.csv) · [用例设计](ISOP-2032/test-cases.md) · [API数据](ISOP-2032/api/data-cases.csv) |
| ISOP-2031 | 新增金額動畫效果 | [设计](ISOP-2031/design.md) · [问题](ISOP-2031/questions.md) · [总用例](ISOP-2031/cases.csv) · [用例设计](ISOP-2031/test-cases.md) · [API数据](ISOP-2031/api/data-cases.csv) |
| ISOP-2030 | 用戶端 - 遊戲頁面改版 | [设计](ISOP-2030/design.md) · [问题](ISOP-2030/questions.md) · [总用例](ISOP-2030/cases.csv) · [用例设计](ISOP-2030/test-cases.md) |
| ISOP-2029 | 用戶端 - 免費旋轉領取文案調整 | [设计](ISOP-2029/design.md) · [问题](ISOP-2029/questions.md) · [总用例](ISOP-2029/cases.csv) · [用例设计](ISOP-2029/test-cases.md) |
| ISOP-2028 | 合規後台 - 統計數據時間調整 | [设计](ISOP-2028/design.md) · [问题](ISOP-2028/questions.md) · [总用例](ISOP-2028/cases.csv) · [用例设计](ISOP-2028/test-cases.md) · [API数据](ISOP-2028/api/data-cases.csv) |
| ISOP-2027 | 管理後台 - KYC 複核功能 | [设计](ISOP-2027/design.md) · [问题](ISOP-2027/questions.md) · [总用例](ISOP-2027/cases.csv) · [用例设计](ISOP-2027/test-cases.md) · [API数据](ISOP-2027/api/data-cases.csv) |
| ISOP-2022 | 管理后台统计数据时间调整 | [设计](ISOP-2022/design.md) · [问题](ISOP-2022/questions.md) · [总用例](ISOP-2022/cases.csv) · [用例设计](ISOP-2022/test-cases.md) · [API数据](ISOP-2022/api/data-cases.csv) · [问题评审](ISOP-2022/bug-review.md) |

每个需求保留三份文档入口：`design.md`写验收规则/影响/测试策略，`questions.md`写问题及答复决定，`test-cases.md`保留验收用例、实现映射与历史证据链接。新执行结果统一生成到结果表，不在Markdown再手工抄写实时通过率。问题解决后同步规则和期望，不将讨论过程塞进用例步骤；索引不复制实时通过率。

排版统一：`questions.md` 的问题列表使用连续表格，每个 Q/D 编号占一行，按原有字段保留状态、来源、待确认答案或决定、建议及影响范围；`test-cases.md` 使用连续表格，统一为 Case ID、优先级/验收点、场景、数据前置、操作步骤、预期结果及副作用检查、方式、依赖/待确认、状态、负责人。表头和数据行之间不插空行；已有编号、历史决定和执行证据保留，未提供的信息明确标注，不为统一格式补造结论。

需求文档、专项 API 数据和场景代码集中在 `requirements/<Jira编号>/`，优先保持单个需求内容清晰。`api/contract-review.md` 记录接口与验收点的对照；接口契约确认后再增加 `api/cases.json` 和必要的场景代码。请求、登录、编码及报告复用 `scripts/filbet/`、`scripts/qa_core/` 的已有能力，不复制底层框架。新需求独立于 P0 门禁；当前API自动执行，UI人工验收，暂不建设新需求UI自动化。P0的API与核心UI自动化继续维护；已有[Telegram专项实现](../docs/telegram-qa.md)仅保留兼容。阶段分工见 [测试流程](workflow.md)。

## 总用例与API数据分开

每个需求自己的`cases.csv`是业务总表，来自`test-cases.md`；有自动执行资产时，`api/data-cases.csv`独立保存具体数据组合、请求和断言。两表通过总用例编号关联，详细数据不再展开到总表。JSON仍是自动执行输入，生成CSV不手工双向维护。当前13个需求均有总表；2022、2027、2028、2031、2032、2037、2043已有API数据表，其余不伪造未实现资产。

`npm run qa:cases -- ISOP-2027`更新单需求，`npm run qa:cases -- --all`更新全部，均不登录。API表包含未具备前提的执行项，不把“有数据表”当作可全量运行；来源和编号规则见[测试流程](../docs/testing-workflow.md#文件与执行入口)。

## 常规需求目录

后续需求按下面的分工组织，文件随设计、实现和实际测试逐步产生，不预建空结果或BUG清单：

```text
requirements/<需求编号>/
├── design.md              # 需求规则、范围与测试策略
├── questions.md           # 待确认问题及决定
├── test-cases.md          # 总用例维护源，包含API与人工UI场景
├── cases.csv              # 简洁总用例生成视图，不展开数据组合
├── plan.json              # 接入统一执行器时的配置，包含人工交付说明
├── api/
│   ├── contract-review.md # 接口契约对照
│   └── data-cases.csv     # 实现API执行配置后生成的数据组合表
└── bug-review.md           # 有实际候选后整理，API与人工UI问题合并评审
```

新接入统一执行器以`plan.json`维护执行配置；旧查询执行器的`api/cases.json`入口仍兼容，不要求同一数据维护两遍。需要独立准备清单时再增加`preparation.csv`。候选BUG清单关联本轮结果和证据，确认后补充Jira编号；文件存在不代表已获提交批准，该文件约定也不代表执行器会自动完成BUG评审。

独立执行的新结果和人工回填放在`reports/qa/<需求编号>/<执行批次或交付包>/`，按用途生成`results.csv`/`results.html`、`manual.csv`及必要证据，详见[团队流程](../docs/team-testing.md)。从Telegram任务执行时，原始API结果仍在reports/qa，团队包、人工导入和统一BUG评审位于`reports/telegram/runs/<job>/`，与活动任务绑定。新需求不再建立UI自动化目录；人工UI场景保留在总用例和人工执行清单中。

ISOP-2022已接入plan.json及API数据表，首轮与限定复核结果见[问题评审](ISOP-2022/bug-review.md)；候选未获建单确认，部分API组合实测不等于父需求全量验收。ISOP-2027多出的`execution-*.md`、`coverage-*.md`和`ui/execution-*.md`是试点阶段记录，不作为新需求的必备模板；其既有BUG清单路径保持兼容。`plan.json`和`preparation.csv`是通用配置与准备资料，并非UI专属文件。

## 开始一个需求

提供需求编号/说明、验收标准、接口或页面变更、目标环境。已有截图、接口文档和开发改动链接可一并提供；尚不确定的业务预期先记录为待确认。

复制 [设计模板](_template/design.md)、[问题模板](_template/questions.md)、[用例模板](_template/test-cases.md) 到 `requirements/<需求编号>/`，保留三个文件名，围绕一个明确变更设计。凭据使用已有本地配置；不要将 token 或用户资料粘贴到需求文档。

## 从设计到回归

1. **明确预期**：把需求验收点编号，区分明确规则、待确认问题和不涉及范围。
2. **分析影响**：定位变更接口/页面、角色、数据状态与上下游，关联现有 P0 用例；查询优先 API，真实页面行为由 UI 提供证据。
3. **形成用例**：覆盖正向、业务拒绝、边界、权限、状态流转及适用的重复提交/幂等；每条写明数据前置、动作、预期业务结果和副作用检查。
4. **实现并验证**：复用现有 runner/公共能力，在需求用例中维护 Case ID → 实现文件/测试名称 → 执行入口 → 回归归属的映射（见模板）。设计阶段不自动执行写入；执行时按需求确定账号、金额、操作范围和恢复方式。先本地检查，再对明确环境执行。
5. **输出结论**：分别记录通过、失败、未执行和阻塞，关联需求验收点与本轮证据；不能把“请求未报错”当成业务通过。
6. **沉淀稳定资产**：按变更风险决定是否纳入 P0、模块回归或保留为专项。正式加入门禁时更新相应清单；低频低风险接口无需为补数量单独建设。

## 文件和结果放哪里

| 内容 | 位置 |
| --- | --- |
| 需求来源、明确规则、影响及测试策略 | `requirements/<需求编号>/design.md` |
| 文档问题、待确认项、答复与最终决定 | `requirements/<需求编号>/questions.md` |
| 验收用例、负责人、实现映射及历史证据链接 | `requirements/<需求编号>/test-cases.md`；简洁审阅表和结果入口见统一测试流程 |
| 需求 API 数据与场景代码 | `requirements/<Jira编号>/api/`；按 Case ID 关联验收用例 |
| API 公共能力 | `scripts/filbet/` 的请求/认证/业务能力，`scripts/qa_core/` 的通用支持 |
| 新需求 UI 验收 | 总用例保留人工UI场景，交付包内manual.csv供人工执行回填；不新增UI自动化，已有实现与P0入口保持兼容 |
| 候选BUG与确认记录 | 新需求有实际候选后维护bug-review.md；既有ISOP-2027清单保持原路径，提交需确认具体清单 |
| API/UI 原始执行证据 | 统一执行器及交付包在reports/qa/<需求编号>/，旧查询入口保留api/results；记录命令、代码版本、环境和时间 |
| 长期故障与方法 | `harness/`、`skills/` |
| 旧扫描退出说明 | [扫描退出索引](../archive/interface-scans/README.md) |

P0运行结果会被清理覆盖；新需求统一执行器按次保存到reports/qa，旧查询入口仍保留各需求api/results路径。本地忽略产物也不等于持久证据存储。用例文件中保留脱敏结论，并在具备 CI/证据存储时记录持久链接。当前 CI 尚未验收，不宣称已自动阻断发布。

新需求使用 `python3 scripts/run-requirement-api.py ISOP-2027 ISOP-2032 ISOP-2037 ISOP-2043` 离线校验；显式增加 `--env .env.fat --execute --insecure` 才执行查询正反例。结果放在各需求 `api/results/<运行标识>/`，P0清理器不清理此目录。用例前置/执行边界和本轮结论见各需求api/README.md。

## 本期接口评审

接口文档基线为 backend_api 的 `365c785..69c9be0`（2026-09-08至09-10），提交关联按内容推断，不视为部署完成。CoinPH 及无本期需求依据的临时调试请求不纳入。

| 需求 | 接口评审 |
| --- | --- |
| ISOP-2043 | [契约对照](ISOP-2043/api/contract-review.md) |
| ISOP-2037 | [契约对照](ISOP-2037/api/contract-review.md) |
| ISOP-2032 | [契约对照](ISOP-2032/api/contract-review.md) |
| ISOP-2027 | [契约对照](ISOP-2027/api/contract-review.md) |
| ISOP-2022 | [契约对照](ISOP-2022/api/contract-review.md) |

## 简洁用例与结果

新需求专项采用CSV用例、前置清单和四状态结果树，详见[用例与结果流程](../docs/testing-workflow.md)。旧结果已按用户授权清理，日期结论不等于本次实测；登录和数据准备不计业务PASS，脚本错误不直接计产品FAIL。

当前新需求交付采用[API自动执行与UI人工验收](../docs/team-testing.md)。人工步骤也维护在plan.json，CSV是生成/回填界面；暂不建设新需求UI自动化；P0的API与核心UI自动化保持。

2026-09-11：[2022—2072已提交接口与未测范围](api-coverage-review-20260911.md)，区分首次未测、历史部分已测、待修复及尚无接口提交依据；不将旧证据清理误记为从未测试。
