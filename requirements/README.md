# 需求设计与测试入口

2026-10-05按用户决定，当前仅保留ISOP-2100；其余32条从[历史索引](history/README.md)查阅。归档不代表新增完成、上线或PASS。已退出证据和本次清理范围统一见[整理记录](../docs/project-cleanup-2026-10-05.md)。

当前工作从下面的入口阅读，日期快照不再混入日常待办：

| 内容 | 入口与用途 |
| --- | --- |
| 本期验收结论 | [10-05核查说明](ISOP-2100/acceptance-20261005.md) · [HTML报告](../reports/qa/ISOP-2100/20261005-requirement-review/views/report.html)，按本期需求正文收敛范围 |
| 当前BUG与交付 | [问题清单](ISOP-2100/questions.md#current-bugs) · [Jira及群同步记录](ISOP-2100/bug-delivery-20261005.md) |
| 最新补测依据 | [10-05补测说明](ISOP-2100/verification-20261005-followup.md) · [HTML报告](../reports/qa/ISOP-2100/20261005-followup/views/report.html)，含本轮未覆盖边界 |
| 前批测试明细 | [10-02执行与BUG报告](../reports/qa/ISOP-2100/20261002-bugs/views/bugs.html)，保留原日期及范围 |
| 需求状态 | [状态列表](status.html)，自动证据与人工修订独立保存 |

## 日常工作

| 要做的事 | 权威说明 |
| --- | --- |
| 评审功能预期、API断言、用例卡片和总表 | [测试流程](../docs/testing-workflow.md) · [文档格式](document-style.md) |
| 合读Jira、评论、关联文档和子任务 | [证据同步](evidence-sync-plan.md)，本地hash检查不代表远端已刷新 |
| 准备接口能力、独立预期和数据 | [API评估标准](api-readiness.md) |
| API执行、人工UI清单与结果回填 | [团队测试](../docs/team-testing.md) · [命令范围](../docs/commands.md) |
| 状态修订、归档和自动执行门槛 | [工作流](../docs/requirement-workflow-cli.md) |
| BUG提单、负责人、群汇总和已解决回归通知 | [当前交付流程](../docs/telegram-qa.md#bug-delivery) |
| 关联已有功能与长期规则 | [模块基线](../modules/README.md) · [业务规则](../skills/business-rules.md) |

功能预期和API断言先由人工确认，AI按明确目标加速执行。新需求API自动执行，UI人工验收；P0继续维护API与核心UI自动化。通用功能模板、JMeter／Postman导出和测试空间简体副本仍待落地，具体缺口见[当前优化项](../docs/new-requirement-automation-plan.md#下一步)。

## 需求索引与组织约定

当前需求放在`requirements/<Jira编号>/`；按用户决定实体归档到`history/<批次>/`，显式编号CLI兼容查询历史。默认扫描、批量导出和工作流只处理当前需求，旧队列不能恢复归档需求执行。

同一需求的补充、复测和重新打开维护原目录；新Jira需求建新目录。业务编号保持稳定，验收点／用例按编号正序，版本索引按创建时间倒序。历史规则必须核对适用差异，不能继承历史PASS或执行豁免。历史日期快照集中在[历史索引](history/README.md)，不作为当前待办。

## 当前需求

当前仅ISOP-2100一条。其余32条需求及跨需求日期快照见[历史记录](history/README.md)；默认扫描、批量导出只处理顶层当前目录。

| Jira 编号 | 需求名称 | 分离文档 |
| --- | --- | --- |
| ISOP-2100 | 代理後台調整 | [设计](ISOP-2100/design.md) · [问题](ISOP-2100/questions.md) · [总用例](ISOP-2100/cases.csv) · [用例设计](ISOP-2100/test-cases.md) |

### 文档组织

每个需求保留三份文档入口：`design.md`写验收规则/影响/测试策略，`questions.md`写问题及答复决定，`test-cases.md`供人评审功能用例。评审主要阅读questions与功能用例；`cases.csv`集中查看功能/API用例覆盖和登记状态，API数据组合供AI准备和执行接口测试。新执行结果统一生成到结果表，不在Markdown再手工抄写实时通过率。问题解决后同步规则和期望，不将讨论过程塞进用例步骤。

排版统一：`questions.md`沿用[问题写法](document-style.md#问题文档的阅读顺序)。`test-cases.md`新版采用短名称索引和“前置条件→操作步骤→预期结果→待确认”卡片，优先级/验收点/方式及实现说明后置，见[功能用例写法](document-style.md#功能用例的阅读顺序)。历史归档的旧宽表保持兼容。已有编号、历史决定和执行证据保留，未提供的信息明确标注，不为统一格式补造结论。

需求文档、专项 API 数据和场景代码集中在 `requirements/<Jira编号>/`，优先保持单个需求内容清晰。`api/contract-review.md` 记录接口与验收点的对照；接口契约确认后再增加 `api/cases.json` 和必要的场景代码。请求、登录、编码及报告复用 `scripts/filbet/`、`scripts/qa_core/` 的已有能力，不复制底层框架。新需求独立于 P0 门禁；当前API自动执行，UI人工验收，暂不建设新需求UI自动化。P0的API与核心UI自动化继续维护；已有新需求UI专项实现仅保留兼容，Telegram统一API／人工包编排继续使用[日常流程](../docs/telegram-qa.md)。阶段分工见 [测试流程](workflow.md)。

## 总用例与API数据分开

每个需求的`cases.csv`是总用例表，合并`test-cases.md`中的功能用例及存在时的`api/test-cases.md`中的API用例；功能在前、API在后。新版总表保留状态、负责人和验证方式，便于查看覆盖与登记进度；功能包含原UI及跨API/UI场景。状态来自用例登记，不会把“已实现”或某一接口组合通过自动算成功能通过，实际结果仍须查看对应批次报告。

有自动执行资产时，`api/data-cases.csv`独立保存具体数据组合、请求和断言，供AI核对和执行接口测试；与总表通过稳定用例编号关联，一条总用例可对应多组数据。JSON仍是执行器输入，CSV由它生成，不手工双向维护。旧宽表导出保留原九列CSV及API/UI/FLOW类型；执行报告和人工回填格式不变。没有执行配置的需求不生成API数据表。

`npm run qa:cases -- ISOP-2100`更新单需求，`npm run qa:cases -- --all`更新当前需求；增加`--include-history`才覆盖历史需求，均不登录。API表包含未具备前提的执行项，不把“有数据表”当作可全量运行；来源和编号规则见[测试流程](../docs/testing-workflow.md#文件与执行入口)。

## 常规需求目录

后续需求按下面的分工组织，文件随设计、实现和实际测试逐步产生，不预建空结果或BUG清单：

```text
requirements/<需求编号>/
├── design.md              # 需求规则、范围与测试策略
├── questions.md           # 待确认问题及决定
├── test-cases.md          # 供人评审的功能用例，短索引与详情卡片
├── cases.csv              # 功能在前/API在后的总表，含登记状态与负责人
├── plan.json              # 接入统一执行器时的配置，包含人工交付说明
├── api/
│   ├── contract-review.md # 接口契约对照
│   ├── test-cases.md      # 有独立API设计时才创建，合并进入总表
│   └── data-cases.csv     # 实现API执行配置后生成的数据组合表
└── bug-review.md           # 有实际候选后整理，API与人工UI问题合并评审
```

新接入统一执行器以`plan.json`维护执行配置；旧查询执行器的`api/cases.json`入口仍兼容，不要求同一数据维护两遍。需要独立准备清单时再增加`preparation.csv`。候选BUG清单关联本轮结果和证据，确认后补充Jira编号；文件存在不代表已获提交批准，该文件约定也不代表执行器会自动完成BUG评审。

独立执行的新结果和人工回填放在`reports/qa/<需求编号>/<执行批次或交付包>/`，按用途生成`results.csv`/`results.html`、`manual.csv`及必要证据，详见[团队流程](../docs/team-testing.md)。从Telegram任务执行时，原始API结果仍在reports/qa，团队包、人工导入和统一BUG评审位于`reports/telegram/runs/<job>/`，与活动任务绑定。新需求不再建立UI自动化目录；人工UI场景保留在总用例和人工执行清单中。

历史试点的`execution-*.md`、`coverage-*.md`和`ui/execution-*.md`不作为新需求的必备模板；既有BUG清单路径保持兼容。`plan.json`和`preparation.csv`是通用配置与准备资料，并非UI专属文件。

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

已有旧查询配置可使用`python3 scripts/run-requirement-api.py <编号>`离线校验；显式增加`--env .env.fat --execute --insecure`才执行查询正反例。结果仍放在各需求`api/results/<运行标识>/`，P0清理器不处理此目录；有目录或报告不代表已有自动执行计划。

## 简洁用例与结果

执行报告使用通过、失败、未执行和执行出错四种状态。登录和数据准备不计业务PASS，脚本错误不直接计产品FAIL。新需求用例、断言及必要恢复逻辑放在需求资产或可导入模块中；新结果目录只保存输出和证据，不新增可执行脚本。既有2100临时采集／报告构建脚本因仍有依赖保留，复用前迁入模块，不从结果目录导入执行能力。

同一批次保留当前报告和必要原始证据，重建时不额外保存`before-*`页面副本；已有兼容CLI的输出契约保持。清理前核对BUG、活动任务和恢复依赖，SQLite、游标、去重状态、账号与号码预留单独保护。被删除证据须在原记录或整理说明标明退出，不能靠删除失败记录改变结论。
