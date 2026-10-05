# ISOP-2028：API测试说明

2026-10-05证据退出：本文引用的非2100静态测试结果已按用户授权清理，日期结论保留为当时记录，不代表当前实测；范围见[整理记录](../../../../../docs/project-cleanup-2026-10-05.md)。

[设计](../design.md) · [问题与决定](../questions.md) · [业务用例](../test-cases.md) · [API数据](data-cases.csv) · 班车报告（原文件已退出，历史路径：`../../../../../reports/qa/batch-20260914-seven/ISOP-2028/results.html`）

[执行计划](../plan.json) · [2026-09-11历史结果与边界](../../../../../docs/history/requirement-records-20260907-11.md#test-20260911)

离线校验并导出：`python3 scripts/run-requirement.py ISOP-2028 --export-cases`。FAT实际执行：`python3 scripts/run-requirement.py ISOP-2028 --env .env.fat --execute --insecure`。报告写入reports/qa/ISOP-2028/独立批次，不覆盖原始证据。

仅执行计划中的只读查询与鉴权；缺少样本/契约的组合保持未执行。正例列表非空才检查行字段，空列表不冒充字段已验。接口通过不代表UI动画、独立金额对账或整个需求验收。
