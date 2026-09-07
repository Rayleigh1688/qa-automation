# 新需求 AI 自动化测试设计

日常 P0 回归入口仍在 [README](../README.md)。这里按需求组织设计与执行证据，不要求先覆盖全部接口，也不因新需求自动扩展 P0。

## 需求索引与组织约定

按 Jira 编号建立 `requirements/<Jira编号>/`，不再按年/月套目录。同一需求的补充、复测与重新打开继续维护原目录；新的 Jira 需求建新目录并链接相关需求。日期、来源版本和执行批次记录在文档中。

按创建时间倒序；本轮选取依据、跨需求依赖和建议分工见 [批次评审](review-summary.md)。

| Jira 编号 | 需求名称 | 分离文档 |
| --- | --- | --- |
| ISOP-2070 | Funky 時間回傳問題 | [设计](ISOP-2070/design.md) · [问题](ISOP-2070/questions.md) · [用例](ISOP-2070/test-cases.md) |
| ISOP-2043 | 管理後台 - 新增 JP 資訊 | [设计](ISOP-2043/design.md) · [问题](ISOP-2043/questions.md) · [用例](ISOP-2043/test-cases.md) |
| ISOP-2041 | JP 注單寫入方式調整 | [设计](ISOP-2041/design.md) · [问题](ISOP-2041/questions.md) · [用例](ISOP-2041/test-cases.md) |
| ISOP-2038 | 合規後台 - 移除 Jackpot 記錄選單 | [设计](ISOP-2038/design.md) · [问题](ISOP-2038/questions.md) · [用例](ISOP-2038/test-cases.md) |
| ISOP-2037 | 合規後台 - 全平台投注紀錄增加欄位 | [设计](ISOP-2037/design.md) · [问题](ISOP-2037/questions.md) · [用例](ISOP-2037/test-cases.md) |
| ISOP-2032 | 用戶端 - 投注返利活動 | [设计](ISOP-2032/design.md) · [问题](ISOP-2032/questions.md) · [用例](ISOP-2032/test-cases.md) |
| ISOP-2031 | 用戶端 - 新增金額動畫效果 | [设计](ISOP-2031/design.md) · [问题](ISOP-2031/questions.md) · [用例](ISOP-2031/test-cases.md) |
| ISOP-2030 | 用戶端 - 遊戲頁面改版 | [设计](ISOP-2030/design.md) · [问题](ISOP-2030/questions.md) · [用例](ISOP-2030/test-cases.md) |
| ISOP-2029 | 用戶端 - 免費旋轉領取文案調整 | [设计](ISOP-2029/design.md) · [问题](ISOP-2029/questions.md) · [用例](ISOP-2029/test-cases.md) |
| ISOP-2028 | 合規後台 - 統計數據時間調整 | [设计](ISOP-2028/design.md) · [问题](ISOP-2028/questions.md) · [用例](ISOP-2028/test-cases.md) |
| ISOP-2027 | 管理後台 - KYC 複核功能 | [设计](ISOP-2027/design.md) · [问题](ISOP-2027/questions.md) · [用例](ISOP-2027/test-cases.md) |
| ISOP-2022 | 管理后台统计数据时间调整 | [设计](ISOP-2022/design.md) · [问题](ISOP-2022/questions.md) · [用例](ISOP-2022/test-cases.md) |

每个需求固定三份文件：`design.md` 写验收规则/影响/测试策略，`questions.md` 写问题及答复决定，`test-cases.md` 写独立可执行用例/负责人/结果与证据。问题解决后同步规则和期望，不将讨论过程塞进用例步骤。状态按验收点和用例维护；索引不复制实时通过率。

需求资料按 Jira 编号组织，可复用测试代码按业务模块维护，并在需求用例中链接实现。不要为每个需求复制登录、环境配置、runner 或报告器。阶段分工见 [测试流程](workflow.md)。

## 开始一个需求

提供需求编号/说明、验收标准、接口或页面变更、目标环境。已有截图、接口文档和开发改动链接可一并提供；尚不确定的业务预期先记录为待确认。

复制 [设计模板](_template/design.md)、[问题模板](_template/questions.md)、[用例模板](_template/test-cases.md) 到 `requirements/<需求编号>/`，保留三个文件名，围绕一个明确变更设计。凭据使用已有本地配置；不要将 token 或用户资料粘贴到需求文档。

## 从设计到回归

1. **明确预期**：把需求验收点编号，区分明确规则、待确认问题和不涉及范围。
2. **分析影响**：定位变更接口/页面、角色、数据状态与上下游，关联现有 P0 用例；查询优先 API，真实页面行为由 UI 提供证据。
3. **形成用例**：覆盖正向、业务拒绝、边界、权限、状态流转及适用的重复提交/幂等；每条写明数据前置、动作、预期业务结果和副作用检查。
4. **实现并验证**：复用现有 runner/公共能力。设计阶段不自动执行写入；执行时按需求确定账号、金额、操作范围和恢复方式。先本地检查，再对明确环境执行。
5. **输出结论**：分别记录通过、失败、未执行和阻塞，关联需求验收点与本轮证据；不能把“请求未报错”当成业务通过。
6. **沉淀稳定资产**：按变更风险决定是否纳入 P0、模块回归或保留为专项。正式加入门禁时更新相应清单；低频低风险接口无需为补数量单独建设。

## 文件和结果放哪里

| 内容 | 位置 |
| --- | --- |
| 需求来源、明确规则、影响及测试策略 | `requirements/<需求编号>/design.md` |
| 文档问题、待确认项、答复与最终决定 | `requirements/<需求编号>/questions.md` |
| 用例、分派、实际结果、复测与验收结论 | `requirements/<需求编号>/test-cases.md` |
| API 可复用实现 | 现有 runner 或 `scripts/qa_core/`；先按设计确定扩展点 |
| UI 可复用实现 | `ui/cases/`、`ui/elements/`、`ui/data/` |
| API/UI 原始执行证据 | 现有忽略结果目录；用例文件标注命令、代码版本、环境和时间 |
| 长期故障与方法 | `harness/`、`skills/` |
| 历史接口发现 | [扫描归档索引](../archive/interface-scans/README.md) |

运行结果会被清理覆盖；只有结果目录路径不足以长期追溯。用例文件中保留脱敏结论，并在具备 CI/证据存储时记录持久链接。当前 CI 尚未验收，不宣称已自动阻断发布。

新增需求执行器时应隔离专项结果，避免覆盖日常 P0 报告；具体子目录、清理范围和命令在实现时核对现有入口后记录，不能假定当前 runner 已支持按需求隔离。
