# ISOP-2027：2026-09-10 FAT 接口测试记录

> 留存说明（2026-09-11）：本文是原日期的文字结论。用户已授权删除旧结果、扫描和临时脚本，文内旧路径只表示历史来源，不能作为当前可复核/可导入证据；当前入口与保留范围见[清理记录](../../../docs/project-cleanup-2026-09-11.md)。

[正反例数据](cases.json) · [契约评审](contract-review.md) · [验收用例](../test-cases.md)

执行环境沿用设计FAT；部署版本未提供。先生成数据，完成本地断言校验，再执行真实API。复用本轮新登录，未使用旧token；未编辑配置、审批会员、创建投注、派奖或导出任务。

按组合ID取本轮最新结果：**6个已调用组合，PASS 5，FAIL 1**。FAIL表示当前断言不满足，分类见下表；不能全部视为已确认产品缺陷。另有17条验收闭环因契约/样本/UI未完成保留BLOCKED，未用查询PASS完成整单。

## 发现与处理

| 编号 | 分类 | 组合ID | 实际证据 | 后续处理 |
| --- | --- | --- | --- | --- |
| F-01 | 契约差异，待确认 | review-list-state-1 | 待复核无记录时data.d为null，文档为array；第一次及复测结构断言失败。中间只读诊断看到1条记录返回list，说明测试数据同时在变化 | 明确空列表是否统一[]；未因中途非空成功覆盖空结果失败 |
| F-02 | 已修正测试识别并复测通过 | auth-missing / auth-invalid | FAT返回HTTP200、status=false、data="token"；是拒绝标记，并非返回凭据 | 仅允许这一精确标记；任意字符串或包含资料对象均不能判PASS |

## 执行与复测

| 轮次 | 命令/范围 | 证据 |
| --- | --- | --- |
| 首次 | python3 scripts/run-requirement-api.py ISOP-2027 ISOP-2032 ISOP-2037 ISOP-2043 --env .env.fat --execute --insecure | results/20260910T064048360549Z/report.md与result.json |
| 定向复测 | 同命令增加 --only auth-missing auth-invalid review-list-state-1 rebate-detail-sums；只选本需求命中的组合 | results/20260910T064317776852Z/report.md与result.json |

首次受沙箱网络限制导致登录失败的记录另存于results/20260910T064035891256Z，未发送业务请求；解除网络限制后才是上表真实执行。首次失败未覆盖，复测仅更新相同组合的最新结论。结果目录是本地忽略产物，此文件保存脱敏长期结论，未上传Jira评论或缺陷。
