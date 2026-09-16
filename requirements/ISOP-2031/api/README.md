# ISOP-2031：API测试说明

[设计](../design.md) · [问题与决定](../questions.md) · [业务用例](../test-cases.md) · [API数据](data-cases.csv) · [班车报告](../../../reports/qa/batch-20260914-seven/ISOP-2031/results.html)

[执行计划](../plan.json) · [2026-09-11历史结果与边界](../../../docs/history/requirement-records-20260907-11.md#test-20260911)

离线校验并导出：`python3 scripts/run-requirement.py ISOP-2031 --export-cases`。FAT实际执行：`python3 scripts/run-requirement.py ISOP-2031 --env .env.fat --execute --insecure`。报告写入reports/qa/ISOP-2031/独立批次，不覆盖原始证据。

仅执行计划中的只读查询与鉴权；缺少样本/契约的组合保持未执行。正例列表非空才检查行字段，空列表不冒充字段已验。接口通过不代表UI动画、独立金额对账或整个需求验收。
