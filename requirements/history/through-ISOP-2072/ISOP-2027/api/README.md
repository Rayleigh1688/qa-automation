# ISOP-2027：API测试说明

2026-10-05证据退出：本文引用的非2100静态测试结果已按用户授权清理，日期结论保留为当时记录，不代表当前实测；范围见[整理记录](../../../../../docs/project-cleanup-2026-10-05.md)。

[设计](../design.md) · [问题与决定](../questions.md) · [业务用例](../test-cases.md) · [API数据](data-cases.csv) · 班车报告（原文件已退出，历史路径：`../../../../../reports/qa/batch-20260914-seven/ISOP-2027/results.html`）

最新限定复测：[历史报告已清理；查看最新FAT报告](../test-report-2026-09-14.md)。FAT人工通过按用户确认登记；接口反例仍有失败，不能据此替换人工结果或宣布UAT验收完成。

[契约评审](contract-review.md) · [正反例数据](cases.json)

用例数据按需求归属；共享执行器复用现有CBOR和后台登录。`case_ids`引用验收Case，`id`标识数据组合；列表结构、筛选命中和完整业务闭环分别记结果。空列表不能使筛选/金额断言通过。

```bash
python3 scripts/run-requirement-api.py ISOP-2027
python3 scripts/run-requirement-api.py ISOP-2027 --env .env.fat --execute --insecure
```

第一条仅离线校验，不登录。第二条示例为FAT，执行时明确选环境；UAT改为.env.uat。固定查询窗口写在cases.json，使用接口规定的毫秒值。默认仅登录和明确的查询路由；不生成导出任务、不编辑配置、不审批已有会员。前置缺失的业务用例保留BLOCKED，补齐专用样本及场景代码后执行。

结果每次写到本目录 `results/<UTC运行标识>/result.json` 和 `report.md`，不会覆盖历史或P0报告；不保存响应正文、凭据或个人资料。登录失败阻塞业务调用。退出码0表示组合全通过，1表示执行失败，2表示仍有阻塞。主验收表含UI和业务闭环，不能将部分API通过整行回写PASS。

首轮只读结论见 [历史报告已清理；查看最新FAT报告](../test-report-2026-09-14.md)。定向复测可增加 `--only <组合ID> ...`，每次产生独立证据。

用户另行授权的受控读写与边界见[FAT日期记录](../test-report-2026-09-14.md)，[候选BUG统一确认入口](BUG-review-2026-09-10.md)保留当时尚未提交的结论。上述受控场景使用本轮独立会员，不由通用只读命令隐式执行；原始测试证据已退出，日期记录不能直接用于当前批次复核。

本需求审阅入口：[简洁CSV用例](../cases.csv)、[前置清单](../preparation.csv)。2026-09-11团队执行包原位于本机`reports/qa/ISOP-2027/team-ready-20260911/`，该包已于2026-10-05退出；旧历史归并和API批次的原始结果也已清理，不再存在。准备视图不表示执行通过，后续需重新生成执行包并补当前证据，不能从已退出文件导入或据此提交BUG。

## 统一API执行入口

当前执行源为[plan.json](../plan.json)，[API数据表](data-cases.csv)及本目录cases.json由它生成。[总用例表](../cases.csv)从test-cases.md生成，只列业务场景，不展开数据集或JSON断言。不要手工改生成CSV。旧只读命令保持原路径/产物；新入口默认仅离线校验。

```bash
npm run qa:requirement -- ISOP-2027 --export-cases
npm run qa:requirement -- ISOP-2027 --env .env.fat --execute --insecure --allow-write kyc-review --allow-write kyc-permissions
```

新命令仅允许FAT；写入范围按所选用例校验。`--only <编号...>`选择本轮用例，`--layer API`仅选API类型；正常跨账号核准/驳回属于FLOW，完整API验收不要误用层级过滤排除这两条。actor A读取既有环境，actor B读取`QA_REVIEWER_ENV`指向的本地覆盖文件（默认`.env.fat.reviewer.local`）；不跨轮复用token。每条写用例持久预留新号码，复用受控注册/KYC能力；无资金写入。权限测试要求B独占当前Codex角色，finally独立恢复原配置。

结果在`reports/qa/ISOP-2027/<run-id>/results.html`和results.csv，原始result.json保留步骤断言、耗时与恢复结果。latest.html/latest.json仅指向最近一次真实执行（可能为定向复验）；历史归并和离线重建不替换它。`private-checkpoints.json`为0600本机记录，保留业务ID与异常现场，不能直接上传。具体本轮结论和剩余边界见[阶段记录](../../../../../docs/new-requirement-stage1-2.md)。

2026-09-14按用户确认更新8项不命中查询：`data.d`使用`empty_or_null`断言，接受`null`或空数组，字段缺失/非空列表/错误类型仍失败；`data.t=0`、HTTP/业务成功和查询无副作用检查保留。匹配查询继续检查具体记录，不统一归一化所有列表。历史结果只离线复评，报告明确标注“通过（规则复评）”，未执行项不改判。
