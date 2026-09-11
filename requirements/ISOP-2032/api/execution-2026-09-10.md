# ISOP-2032：2026-09-10 FAT 接口测试记录

> 留存说明（2026-09-11）：本文是原日期的文字结论。用户已授权删除旧结果、扫描和临时脚本，文内旧路径只表示历史来源，不能作为当前可复核/可导入证据；当前入口与保留范围见[清理记录](../../../docs/project-cleanup-2026-09-11.md)。

[正反例数据](cases.json) · [契约评审](contract-review.md) · [验收用例](../test-cases.md)

执行环境沿用设计FAT；部署版本未提供。先生成数据，完成本地断言校验，再执行真实API。复用本轮新登录，未使用旧token；未编辑配置、审批会员、创建投注、派奖或导出任务。

按组合ID取本轮最新结果：**8个已调用组合，PASS 7，FAIL 1**。FAIL表示当前断言不满足，分类见下表；不能全部视为已确认产品缺陷。另有21条验收闭环因契约/样本/UI未完成保留BLOCKED，未用查询PASS完成整单。

## 发现与处理

| 编号 | 分类 | 组合ID | 实际证据 | 后续处理 |
| --- | --- | --- | --- | --- |
| F-01 | 精度/契约待确认，非已确认产品缺陷 | rebate-detail-sums | 同一报表行bonus=0.4000、multiple_amount=0.40；conf对应金额均为0.405，严格相等断言失败，其余7行本次诊断相等 | Q-05确认截断/舍入方式及发生层级，再分别断言实派与展示；不能擅加误差将其改PASS |
| F-02 | 查询通过的边界 | rebate-report-state-0/1/3/4、rebate-detail-fields | 查询结构与明细金额字段通过；请求/响应state定义仍冲突 | 不证明需手动领取，也不证明T+1计算、入账、幂等正确 |
| F-03 | 已修正测试识别并复测通过 | auth-missing / auth-invalid | HTTP200、status=false、data="token"符合FAT鉴权拒绝 | 不是越权漏洞；保留首次错误识别与复测证据 |

## 执行与复测

| 轮次 | 命令/范围 | 证据 |
| --- | --- | --- |
| 首次 | python3 scripts/run-requirement-api.py ISOP-2027 ISOP-2032 ISOP-2037 ISOP-2043 --env .env.fat --execute --insecure | results/20260910T064048360549Z/report.md与result.json |
| 定向复测 | 同命令增加 --only auth-missing auth-invalid review-list-state-1 rebate-detail-sums；只选本需求命中的组合 | results/20260910T064317776852Z/report.md与result.json |

首次受沙箱网络限制导致登录失败的记录另存于results/20260910T064035891256Z，未发送业务请求；解除网络限制后才是上表真实执行。首次失败未覆盖，复测仅更新相同组合的最新结论。结果目录是本地忽略产物，此文件保存脱敏长期结论，未上传Jira评论或缺陷。
