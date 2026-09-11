# ISOP-2037：2026-09-10 FAT 接口测试记录

> 留存说明（2026-09-11）：本文是原日期的文字结论。用户已授权删除旧结果、扫描和临时脚本，文内旧路径只表示历史来源，不能作为当前可复核/可导入证据；当前入口与保留范围见[清理记录](../../../docs/project-cleanup-2026-09-11.md)。

[正反例数据](cases.json) · [契约评审](contract-review.md) · [验收用例](../test-cases.md)

执行环境沿用设计FAT；部署版本未提供。先生成数据，完成本地断言校验，再执行真实API。复用本轮新登录，未使用旧token；未编辑配置、审批会员、创建投注、派奖或导出任务。

按组合ID取本轮最新结果：**10个已调用组合，PASS 7，FAIL 3**。FAIL表示当前断言不满足，分类见下表；不能全部视为已确认产品缺陷。另有11条验收闭环因契约/样本/UI未完成保留BLOCKED，未用查询PASS完成整单。

## 发现与处理

| 编号 | 分类 | 组合ID | 实际证据 | 后续处理 |
| --- | --- | --- | --- | --- |
| F-01 | 金额不一致，待核对样本/部署 | game-jp-99 | 一笔Multi主单jp_winning=4200000.01000000；两明细100000.00000000+500000.00000000=600000.00000000，相差3600000.01。另一笔600000.05与明细相等 | 不修改预期、不调整源数据；核对主单与奖池明细来源/回填 |
| F-02 | 空结果契约差异 | game-jp-2 | HTTP200/status=true，t=0/s=0，但data.d=null；文档为array | 保留结构FAIL；不能认为Minor筛选业务已验证 |
| F-03 | 必填参数契约差异 | game-missing-time | 缺少全部时间范围，返回HTTP200/status=true/data=null | 需确认是合法空结果还是缺少必填校验，不把成功包装当明确拒绝 |
| F-04 | 已修正测试识别并复测通过 | auth-missing / auth-invalid | 精确识别FAT data="token"拒绝标记 | 无数据泄露证据，非权限缺陷 |

## 执行与复测

| 轮次 | 命令/范围 | 证据 |
| --- | --- | --- |
| 首次 | python3 scripts/run-requirement-api.py ISOP-2027 ISOP-2032 ISOP-2037 ISOP-2043 --env .env.fat --execute --insecure | results/20260910T064048360549Z/report.md与result.json |
| 定向复测 | 同命令增加 --only auth-missing auth-invalid review-list-state-1 rebate-detail-sums；只选本需求命中的组合 | results/20260910T064317776852Z/report.md与result.json |

首次受沙箱网络限制导致登录失败的记录另存于results/20260910T064035891256Z，未发送业务请求；解除网络限制后才是上表真实执行。首次失败未覆盖，复测仅更新相同组合的最新结论。结果目录是本地忽略产物，此文件保存脱敏长期结论，未上传Jira评论或缺陷。
