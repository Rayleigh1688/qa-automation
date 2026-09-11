# ISOP-2043：2026-09-10 FAT 接口测试记录

> 留存说明（2026-09-11）：本文是原日期的文字结论。用户已授权删除旧结果、扫描和临时脚本，文内旧路径只表示历史来源，不能作为当前可复核/可导入证据；当前入口与保留范围见[清理记录](../../../docs/project-cleanup-2026-09-11.md)。

[正反例数据](cases.json) · [契约评审](contract-review.md) · [验收用例](../test-cases.md)

执行环境沿用设计FAT；部署版本未提供。先生成数据，完成本地断言校验，再执行真实API。复用本轮新登录，未使用旧token；未编辑配置、审批会员、创建投注、派奖或导出任务。

按组合ID取本轮最新结果：**22个已调用组合，PASS 16，FAIL 6**。FAIL表示当前断言不满足，分类见下表；不能全部视为已确认产品缺陷。另有9条验收闭环因契约/样本/UI未完成保留BLOCKED，未用查询PASS完成整单。

## 发现与处理

| 编号 | 分类 | 组合ID | 实际证据 | 后续处理 |
| --- | --- | --- | --- | --- |
| F-01 | 金额不一致，待核对样本/部署 | bet-jp-99 / game-jp-99 | 财务与游戏投注入口均未通过Multi金额加总断言；关联2037同查询窗口样本 | 两入口共用逻辑，不能当作两个独立数据源验证正确 |
| F-02 | 空结果契约差异 | bet-jp-2 / game-jp-2 | HTTP200/status=true，data.d不是array | 不放宽结构断言，不将空数据算类型/金额通过 |
| F-03 | 必填参数契约差异 | bet-missing-time / game-missing-time | 缺少两组时间范围仍业务成功，data=null | 确认时间参数校验契约 |
| F-04 | 已修正测试识别并复测通过 | auth-missing / auth-invalid | 精确识别FAT data="token"拒绝标记 | 不以首次测试识别失败宣称越权 |

## 执行与复测

| 轮次 | 命令/范围 | 证据 |
| --- | --- | --- |
| 首次 | python3 scripts/run-requirement-api.py ISOP-2027 ISOP-2032 ISOP-2037 ISOP-2043 --env .env.fat --execute --insecure | results/20260910T064048360549Z/report.md与result.json |
| 定向复测 | 同命令增加 --only auth-missing auth-invalid review-list-state-1 rebate-detail-sums；只选本需求命中的组合 | results/20260910T064317776852Z/report.md与result.json |

首次受沙箱网络限制导致登录失败的记录另存于results/20260910T064035891256Z，未发送业务请求；解除网络限制后才是上表真实执行。首次失败未覆盖，复测仅更新相同组合的最新结论。结果目录是本地忽略产物，此文件保存脱敏长期结论，未上传Jira评论或缺陷。
