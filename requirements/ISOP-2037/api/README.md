# ISOP-2037 API 测试

[验收用例](../test-cases.md) · [契约评审](contract-review.md) · [正反例数据](cases.json)

用例数据按需求归属；共享执行器复用现有CBOR和后台登录。`case_ids`引用验收Case，`id`标识数据组合；列表结构、筛选命中和完整业务闭环分别记结果。空列表不能使筛选/金额断言通过。

```bash
python3 scripts/run-requirement-api.py ISOP-2037
python3 scripts/run-requirement-api.py ISOP-2037 --env .env.fat --execute --insecure
```

第一条仅离线校验，不登录。第二条示例为FAT，执行时明确选环境；UAT改为.env.uat。固定查询窗口写在cases.json，使用接口规定的毫秒值。默认仅登录和明确的查询路由；不生成导出任务、不编辑配置、不审批已有会员。前置缺失的业务用例保留BLOCKED，补齐专用样本及场景代码后执行。

结果每次写到本目录 `results/<UTC运行标识>/result.json` 和 `report.md`，不会覆盖历史或P0报告；不保存响应正文、凭据或个人资料。登录失败阻塞业务调用。退出码0表示组合全通过，1表示执行失败，2表示仍有阻塞。主验收表含UI和业务闭环，不能将部分API通过整行回写PASS。

本轮结论见 [2026-09-10 FAT 执行记录](execution-2026-09-10.md)。定向复测可增加 `--only <组合ID> ...`，每次产生独立证据。

本需求[总用例](../cases.csv)与[API数据驱动用例](data-cases.csv)分开；后者由本目录cases.json生成，保留请求、断言、总用例关联及前置缺口。更新命令：`npm run qa:cases -- ISOP-2037`，不登录。
