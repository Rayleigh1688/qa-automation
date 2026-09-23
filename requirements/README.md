# 需求设计与版本索引

现有功能先对照[业务模块基线](../modules/README.md)：按菜单维护长期规则与覆盖缺口，需求目录记录本次变更、影响和交付。首页BI先整理，KYC随后复用已有规则；模块观察不替代需求验收。

所有需求文档遵循[统一格式约束](document-style.md)：章节保留原文编号和`§`、问题编号用`Q-01`、日期格式统一，保留业务用例和执行数据的机器字段。原班车7个需求的记录已随完成批次归档。

问题文档按“简短名称→具体场景→问题点→需要确认”阅读，来源和用例关联放在后面，见[2104示例](ISOP-2104/questions.md)。跨团队Agent如何交接问题、转交人工和追踪答复，先讨论[参考项目与场景](../docs/agent-collaboration-research.md)；平台及消息格式尚未确定。

需求补充先执行[证据同步流程](evidence-sync-plan.md)：合读Jira正文/评论、关联Lark与子任务，将决定同步到设计、用例和执行源；来源版本及未读范围必须可追溯。`npm run qa -- evidence`离线查看同步缺口，首次落地见[2032记录](history/through-ISOP-2072/ISOP-2032/evidence-sync.md)。

设计相关模块前先查[业务规则入口](../skills/business-rules.md)，在design引用编号、版本及适用差异。KYC已有[可复用规则](../skills/business-rules/kyc.md)，无需从历史报告重新梳理；规则确认与实测通过分开记录。

先看[需求状态列表](status.html)：统一查看各Story的提测、测试进度、待修复、上线与关闭状态及下一步；业务用例和报告仍在各自目录维护。

需求出来即按[API准备与评估标准](api-readiness.md)推导接口能力、准备独立预期和正反例；提测后在design.md明确功能覆盖、可测性与实测结论。设计/接口评审模板已补齐，数据结构与链路有影响时使用api/data-review.md；[2028示例](history/through-ISOP-2072/ISOP-2028/design.md#接口能力预期与当前评估)展示当前缺口，回归能力按FAT/UAT分别验收。

日常 P0 回归入口仍在 [README](../README.md)。这里按需求组织设计与执行证据，不要求先覆盖全部接口，也不因新需求自动扩展 P0。

新需求执行能力当前按[API/UI完善计划](../docs/new-requirement-automation-plan.md)分阶段推进；ISOP-2027阶段1、2及固定UI阶段3已交付，证据与剩余事项见[API记录](../docs/new-requirement-stage1-2.md)和[UI记录](../docs/new-requirement-stage3.md)。用户查看以自动生成的`results.csv`/`results.html`为主，保留用例、预期、实际与通过/失败；普通用例逐步迁移为结构化执行数据，尚未迁移的历史资产不视为已可一键重跑。

2026-09-11新交付接口已按顺序开测，中文报告、实际失败和未执行范围见[本轮结果](../docs/history/requirement-records-20260907-11.md#test-20260911)。

## 需求索引与组织约定

- [当前需求：ISOP-2072之后](#当前需求)
- [历史版本：ISOP-2072及之前](history/README.md)

2026-09-18用户确认ISOP-2072及之前已完成，实体归档至`requirements/history/through-ISOP-2072/`。顶层仅保留当前需求；显式编号CLI兼容查找历史目录，历史测试证据不改写为本轮通过。

2026-09-18：[ISOP-2072之后20条独立单初审](review-after-2072-20260918.md)，已逐单落实下表20个目录的设计、问题、用例与CSV，保留来源和未读素材边界；不代表业务验收或新增执行授权。

当前需求按 Jira 编号建立 `requirements/<Jira编号>/`；完成批次移入`history/<版本>/`，本次版本标识为`through-ISOP-2072`。同一需求的补充、复测与重新打开继续维护原目录；新的 Jira 需求建新目录并链接相关需求。日期、来源版本和执行批次记录在文档中。

当前及历史版本索引内部按创建时间倒序；后续新增需求放入当前需求。完成的需求按批次实体归档；用户完成确认与历史实测结论分别保留。单个需求内的验收点和用例按编号正序；问题按便于理解的顺序展开，已有答案单列，稳定编号用于引用。

2026-09-14历史班车范围与实际结果见[七需求记录](test-round-20260914-seven.md)。早期选取依据和跨需求评审保留在[历史评审](../docs/history/requirement-records-20260907-11.md#review-20260907)。

群消息扫描的待确认任务仅以顶层当前需求目录的工单为单位，子任务提测归并到所属需求；无提测记录不因目录存在而列入。终端显示简洁需求列表，详细依据保存在本地preview.json；查看与选择命令见[Telegram流程](../docs/telegram-qa.md#手动扫描一次)。

### 当前需求

编号大于ISOP-2072，共20条独立单。历史13条见[历史版本入口](history/README.md)。

| Jira 编号 | 需求名称 | 分离文档 |
| --- | --- | --- |
| ISOP-2120 | 金幣派發效果二期 | [设计](ISOP-2120/design.md) · [问题](ISOP-2120/questions.md) · [总用例](ISOP-2120/cases.csv) · [用例设计](ISOP-2120/test-cases.md) |
| ISOP-2119 | 管理後台 - 遊戲廠商類型編輯調整 | [设计](ISOP-2119/design.md) · [问题](ISOP-2119/questions.md) · [总用例](ISOP-2119/cases.csv) · [用例设计](ISOP-2119/test-cases.md) |
| ISOP-2118 | 投返二期 | [设计](ISOP-2118/design.md) · [问题](ISOP-2118/questions.md) · [总用例](ISOP-2118/cases.csv) · [用例设计](ISOP-2118/test-cases.md) |
| ISOP-2117 | Daily Rewards 顯示調整 | [设计](ISOP-2117/design.md) · [问题](ISOP-2117/questions.md) · [总用例](ISOP-2117/cases.csv) · [用例设计](ISOP-2117/test-cases.md) |
| ISOP-2116 | PlayTime 遊戲對接 | [设计](ISOP-2116/design.md) · [问题](ISOP-2116/questions.md) · [总用例](ISOP-2116/cases.csv) · [用例设计](ISOP-2116/test-cases.md) |
| ISOP-2111 | [Filplay] 直向手機點大廳遊戲會開到旁邊那一款 | [设计](ISOP-2111/design.md) · [问题](ISOP-2111/questions.md) · [总用例](ISOP-2111/cases.csv) · [用例设计](ISOP-2111/test-cases.md) |
| ISOP-2110 | 編輯彈窗檢查邏輯調整 | [设计](ISOP-2110/design.md) · [问题](ISOP-2110/questions.md) · [总用例](ISOP-2110/cases.csv) · [用例设计](ISOP-2110/test-cases.md) |
| ISOP-2109 | 前端頁面調整 | [设计](ISOP-2109/design.md) · [问题](ISOP-2109/questions.md) · [总用例](ISOP-2109/cases.csv) · [用例设计](ISOP-2109/test-cases.md) |
| ISOP-2104 | 投注返利活動頁 | [设计](ISOP-2104/design.md) · [问题](ISOP-2104/questions.md) · [总用例](ISOP-2104/cases.csv) · [用例设计](ISOP-2104/test-cases.md) |
| ISOP-2103 | 免費旋轉派發彈窗 | [设计](ISOP-2103/design.md) · [问题](ISOP-2103/questions.md) · [总用例](ISOP-2103/cases.csv) · [用例设计](ISOP-2103/test-cases.md) |
| ISOP-2102 | MX API 調整 | [设计](ISOP-2102/design.md) · [问题](ISOP-2102/questions.md) · [总用例](ISOP-2102/cases.csv) · [用例设计](ISOP-2102/test-cases.md) |
| ISOP-2100 | 代理後台調整 | [设计](ISOP-2100/design.md) · [问题](ISOP-2100/questions.md) · [总用例](ISOP-2100/cases.csv) · [用例设计](ISOP-2100/test-cases.md) |
| ISOP-2098 | SA 投注詳情新增 | [设计](ISOP-2098/design.md) · [问题](ISOP-2098/questions.md) · [总用例](ISOP-2098/cases.csv) · [用例设计](ISOP-2098/test-cases.md) |
| ISOP-2094 | [Filplay] 地域限制 | [设计](ISOP-2094/design.md) · [问题](ISOP-2094/questions.md) · [总用例](ISOP-2094/cases.csv) · [用例设计](ISOP-2094/test-cases.md) |
| ISOP-2093 | Gcash 充值後跳轉流程 | [设计](ISOP-2093/design.md) · [问题](ISOP-2093/questions.md) · [总用例](ISOP-2093/cases.csv) · [用例设计](ISOP-2093/test-cases.md) |
| ISOP-2092 | 後台首頁數據看板 | [设计](ISOP-2092/design.md) · [问题](ISOP-2092/questions.md) · [总用例](ISOP-2092/cases.csv) · [用例设计](ISOP-2092/test-cases.md) |
| ISOP-2091 | 廠商排行榜活動 | [设计](ISOP-2091/design.md) · [问题](ISOP-2091/questions.md) · [总用例](ISOP-2091/cases.csv) · [用例设计](ISOP-2091/test-cases.md) |
| ISOP-2090 | 輸值返利活動 | [设计](ISOP-2090/design.md) · [问题](ISOP-2090/questions.md) · [总用例](ISOP-2090/cases.csv) · [用例设计](ISOP-2090/test-cases.md) |
| ISOP-2089 | Search 頁面改版 | [设计](ISOP-2089/design.md) · [问题](ISOP-2089/questions.md) · [总用例](ISOP-2089/cases.csv) · [用例设计](ISOP-2089/test-cases.md) |
| ISOP-2086 | 修改 Nav 的 Reward 為 Promos | [设计](ISOP-2086/design.md) · [问题](ISOP-2086/questions.md) · [总用例](ISOP-2086/cases.csv) · [用例设计](ISOP-2086/test-cases.md) |

### 文档组织

每个需求保留三份文档入口：`design.md`写验收规则/影响/测试策略，`questions.md`写问题及答复决定，`test-cases.md`保留验收用例、实现映射与历史证据链接。新执行结果统一生成到结果表，不在Markdown再手工抄写实时通过率。问题解决后同步规则和期望，不将讨论过程塞进用例步骤；索引不复制实时通过率。

排版统一：`questions.md` 首屏用连续表格列编号、简短名称、状态和答复方，详情按“场景→问题点→需要确认”展开，已有答案单列，来源和用例关联后置；保留原有决定、建议和影响范围，详见[问题写法](document-style.md#问题文档的阅读顺序)。`test-cases.md` 使用连续表格，统一为 Case ID、优先级/验收点、场景、数据前置、操作步骤、预期结果及副作用检查、方式、依赖/待确认、状态、负责人。表头和数据行之间不插空行；已有编号、历史决定和执行证据保留，未提供的信息明确标注，不为统一格式补造结论。

需求文档、专项 API 数据和场景代码集中在 `requirements/<Jira编号>/`，优先保持单个需求内容清晰。`api/contract-review.md` 记录接口与验收点的对照；接口契约确认后再增加 `api/cases.json` 和必要的场景代码。请求、登录、编码及报告复用 `scripts/filbet/`、`scripts/qa_core/` 的已有能力，不复制底层框架。新需求独立于 P0 门禁；当前API自动执行，UI人工验收，暂不建设新需求UI自动化。P0的API与核心UI自动化继续维护；已有[Telegram专项实现](../docs/telegram-qa.md)仅保留兼容。阶段分工见 [测试流程](workflow.md)。

## 总用例与API数据分开

每个需求自己的`cases.csv`是业务总表，来自`test-cases.md`；有自动执行资产时，`api/data-cases.csv`独立保存具体数据组合、请求和断言。两表通过总用例编号关联，详细数据不再展开到总表。JSON仍是自动执行输入，生成CSV不手工双向维护。当前33个独立单目录均有总表（含20个本次初审落地目录）；2022、2027、2028、2031、2032、2037、2043已有API数据表，其余不伪造未实现资产。

`npm run qa:cases -- ISOP-2027`更新单需求，`npm run qa:cases -- --all`更新当前需求；增加`--include-history`才覆盖历史需求，均不登录。API表包含未具备前提的执行项，不把“有数据表”当作可全量运行；来源和编号规则见[测试流程](../docs/testing-workflow.md#文件与执行入口)。

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

ISOP-2022已接入plan.json及API数据表，首轮与限定复核结果见[问题评审](history/through-ISOP-2072/ISOP-2022/bug-review.md)；候选未获建单确认，部分API组合实测不等于父需求全量验收。ISOP-2027多出的`execution-*.md`、`coverage-*.md`和`ui/execution-*.md`是试点阶段记录，不作为新需求的必备模板；其既有BUG清单路径保持兼容。`plan.json`和`preparation.csv`是通用配置与准备资料，并非UI专属文件。

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
| ISOP-2043 | [契约对照](history/through-ISOP-2072/ISOP-2043/api/contract-review.md) |
| ISOP-2037 | [契约对照](history/through-ISOP-2072/ISOP-2037/api/contract-review.md) |
| ISOP-2032 | [契约对照](history/through-ISOP-2072/ISOP-2032/api/contract-review.md) |
| ISOP-2027 | [契约对照](history/through-ISOP-2072/ISOP-2027/api/contract-review.md) |
| ISOP-2022 | [契约对照](history/through-ISOP-2072/ISOP-2022/api/contract-review.md) |

## 简洁用例与结果

新需求专项采用CSV用例、前置清单和四状态结果树，详见[用例与结果流程](../docs/testing-workflow.md)。旧结果已按用户授权清理，日期结论不等于本次实测；登录和数据准备不计业务PASS，脚本错误不直接计产品FAIL。

当前新需求交付采用[API自动执行与UI人工验收](../docs/team-testing.md)。人工步骤也维护在plan.json，CSV是生成/回填界面；暂不建设新需求UI自动化；P0的API与核心UI自动化保持。

2026-09-11：[2022—2072已提交接口与未测范围](../docs/history/requirement-records-20260907-11.md#coverage-20260911)，区分首次未测、历史部分已测、待修复及尚无接口提交依据；不将旧证据清理误记为从未测试。
