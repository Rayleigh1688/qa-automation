# 历史需求与日期记录

[返回当前需求](../README.md#当前需求)

2026-09-18按用户指定边界收录仓库已有13条需求，包含ISOP-2072。用户已确认本批需求均已完成，现按完成归档。旧失败、待确认与未测记录仅保留为日期证据，不重新标为本次测试通过；具体上线版本未新增核验。

需求实体已移入`requirements/history/through-ISOP-2072/ISOP-编号/`。CLI显式传需求编号可查找归档目录；默认扫描、批量用例导出与工作流检查只关注顶层当前需求，归档不再自动触发测试。统一报告仍在`reports/qa/<编号>/`；旧查询报告在2026-09-18随目录迁移，当时未删；2026-10-05按本次授权已清理。

## 2026-10-05范围归档

[本批19条需求索引](archived-20261005/README.md)：来源为用户2026-10-05“除2100都归档”决定，未新增完成或上线确认。当前仅保留ISOP-2100，历史需求合计32条。

本批及既有历史需求的静态测试产物已同次清理，原始证据已退出；保留的日期结论来自原文记录，不代表当前部署实测。配置、设计、问题和用例保留，具体清理与2100依赖保留范围见[整理记录](../../docs/project-cleanup-2026-10-05.md)。

## 已完成批次：ISOP-2072及之前

| Jira 编号 | 需求名称 | 分离文档 |
| --- | --- | --- |
| ISOP-2072 | 報表數據更改爲排程計算 | [设计](through-ISOP-2072/ISOP-2072/design.md) · [问题](through-ISOP-2072/ISOP-2072/questions.md) · [总用例](through-ISOP-2072/ISOP-2072/cases.csv) · [用例设计](through-ISOP-2072/ISOP-2072/test-cases.md) |
| ISOP-2070 | Funky 時間回傳問題 | [设计](through-ISOP-2072/ISOP-2070/design.md) · [问题](through-ISOP-2072/ISOP-2070/questions.md) · [总用例](through-ISOP-2072/ISOP-2070/cases.csv) · [用例设计](through-ISOP-2072/ISOP-2070/test-cases.md) |
| ISOP-2043 | 管理後台 - 新增 JP 資訊 | [设计](through-ISOP-2072/ISOP-2043/design.md) · [问题](through-ISOP-2072/ISOP-2043/questions.md) · [总用例](through-ISOP-2072/ISOP-2043/cases.csv) · [用例设计](through-ISOP-2072/ISOP-2043/test-cases.md) · [API数据](through-ISOP-2072/ISOP-2043/api/data-cases.csv) |
| ISOP-2041 | JP 注單寫入方式調整 | [设计](through-ISOP-2072/ISOP-2041/design.md) · [问题](through-ISOP-2072/ISOP-2041/questions.md) · [总用例](through-ISOP-2072/ISOP-2041/cases.csv) · [用例设计](through-ISOP-2072/ISOP-2041/test-cases.md) |
| ISOP-2038 | 合規後台 - 移除 Jackpot 記錄選單 | [设计](through-ISOP-2072/ISOP-2038/design.md) · [问题](through-ISOP-2072/ISOP-2038/questions.md) · [总用例](through-ISOP-2072/ISOP-2038/cases.csv) · [用例设计](through-ISOP-2072/ISOP-2038/test-cases.md) |
| ISOP-2037 | 合規後台 - 全平台投注紀錄增加欄位 | [设计](through-ISOP-2072/ISOP-2037/design.md) · [问题](through-ISOP-2072/ISOP-2037/questions.md) · [总用例](through-ISOP-2072/ISOP-2037/cases.csv) · [用例设计](through-ISOP-2072/ISOP-2037/test-cases.md) · [API数据](through-ISOP-2072/ISOP-2037/api/data-cases.csv) |
| ISOP-2032 | 用戶端 - 投注返利活動 | [设计](through-ISOP-2072/ISOP-2032/design.md) · [问题](through-ISOP-2072/ISOP-2032/questions.md) · [总用例](through-ISOP-2072/ISOP-2032/cases.csv) · [用例设计](through-ISOP-2072/ISOP-2032/test-cases.md) · [API数据](through-ISOP-2072/ISOP-2032/api/data-cases.csv) |
| ISOP-2031 | 新增金額動畫效果 | [设计](through-ISOP-2072/ISOP-2031/design.md) · [问题](through-ISOP-2072/ISOP-2031/questions.md) · [总用例](through-ISOP-2072/ISOP-2031/cases.csv) · [用例设计](through-ISOP-2072/ISOP-2031/test-cases.md) · [API数据](through-ISOP-2072/ISOP-2031/api/data-cases.csv) |
| ISOP-2030 | 用戶端 - 遊戲頁面改版 | [设计](through-ISOP-2072/ISOP-2030/design.md) · [问题](through-ISOP-2072/ISOP-2030/questions.md) · [总用例](through-ISOP-2072/ISOP-2030/cases.csv) · [用例设计](through-ISOP-2072/ISOP-2030/test-cases.md) |
| ISOP-2029 | 用戶端 - 免費旋轉領取文案調整 | [设计](through-ISOP-2072/ISOP-2029/design.md) · [问题](through-ISOP-2072/ISOP-2029/questions.md) · [总用例](through-ISOP-2072/ISOP-2029/cases.csv) · [用例设计](through-ISOP-2072/ISOP-2029/test-cases.md) |
| ISOP-2028 | 合規後台 - 統計數據時間調整 | [设计](through-ISOP-2072/ISOP-2028/design.md) · [问题](through-ISOP-2072/ISOP-2028/questions.md) · [总用例](through-ISOP-2072/ISOP-2028/cases.csv) · [用例设计](through-ISOP-2072/ISOP-2028/test-cases.md) · [API数据](through-ISOP-2072/ISOP-2028/api/data-cases.csv) |
| ISOP-2027 | 管理後台 - KYC 複核功能 | [设计](through-ISOP-2072/ISOP-2027/design.md) · [问题](through-ISOP-2072/ISOP-2027/questions.md) · [总用例](through-ISOP-2072/ISOP-2027/cases.csv) · [用例设计](through-ISOP-2072/ISOP-2027/test-cases.md) · [API数据](through-ISOP-2072/ISOP-2027/api/data-cases.csv) |
| ISOP-2022 | 管理后台统计数据时间调整 | [设计](through-ISOP-2072/ISOP-2022/design.md) · [问题](through-ISOP-2072/ISOP-2022/questions.md) · [总用例](through-ISOP-2072/ISOP-2022/cases.csv) · [用例设计](through-ISOP-2072/ISOP-2022/test-cases.md) · [API数据](through-ISOP-2072/ISOP-2022/api/data-cases.csv) · [问题评审](through-ISOP-2072/ISOP-2022/bug-review.md) |

## 历史批次与交接

- [2026-09-18二十单初审](records-through-20261005/review-after-2072-20260918.md)
- [2026-09-24 Sprint提测与产品确认快照](records-through-20261005/sprint-2026w25-20260924.md)
- [2026-09-15班车状态](records-through-20261005/status.md) · [2026-09-14迁移基线](records-through-20261005/status-history-20260914.md)

- [2026-09-14七需求测试记录](records-through-20261005/test-round-20260914-seven.md)
- [2026-09-16提测时间核对](records-through-20261005/submission-history-20260916.md)
- [2026-09-07—11历史评审与测试记录](../../docs/history/requirement-records-20260907-11.md)
- [当前交接](../../AI-HANDOFF.md)：仍有效的阻塞、用户决定与下一步。

上述报告按各自日期理解，不作为本次复测。新需求引用历史需求规则时保留明确来源与适用差异，历史缺陷及待确认记录保留原结论；该完成批次的归档依据为用户2026-09-18完成确认；本次新增19条仅依据2026-10-05范围决定。
