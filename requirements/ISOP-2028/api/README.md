# ISOP-2028 API执行

[执行计划](../plan.json) · [API数据](data-cases.csv) · [本轮结果与边界](../../api-test-round-20260911.md)

离线校验并导出：`python3 scripts/run-requirement.py ISOP-2028 --export-cases`。FAT实际执行：`python3 scripts/run-requirement.py ISOP-2028 --env .env.fat --execute --insecure`。报告写入reports/qa/ISOP-2028/独立批次，不覆盖原始证据。

仅执行计划中的只读查询与鉴权；缺少样本/契约的组合保持未执行。正例列表非空才检查行字段，空列表不冒充字段已验。接口通过不代表UI动画、独立金额对账或整个需求验收。
