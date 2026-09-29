# ISOP-2100：证据同步记录

[设计](design.md) · [问题与决定](questions.md) · [测试用例](test-cases.md) · [总用例](cases.csv) · [来源同步](evidence-sync.md)

## 当前来源：2026-09-29

[Jira主单](https://alibaba-international.atlassian.net/browse/ISOP-2100) updated=2026-09-28 10:33:22 +08；完整正文§1—§6、评论17358共1/1。2150/2151/2152/2166/2170五子任务正文为空、返回评论0；开发4项进行中、QA待办。关联2176待办，正文图片未视觉核。主单无Lark链接。

在线原型读取：[代理首页](https://vip-admin-gray.vercel.app/agency/home)、其菜单进入的会员列表/会员日统计、[管理代理统计](https://vip-admin-gray.vercel.app/admin/agency-report)、[带代理的会员统计](https://vip-admin-gray.vercel.app/admin/member-stats?agent=agent_darren&start=2026-09-01&end=2026-09-30)。五张Jira静态附件未单独视觉阅读，不声称与原型逐像素一致。原型示范数据不作业务通过证据。

FB本地HEAD及契约读取范围见[评审](review-20260929.md)。本轮未重新取远端FB分支、未调用FAT/UAT业务API、未读源码或数据库；评论里的代码风险为作者历史查证，未当成本轮复现。

## 同步影响

| 变化 | 来源 | 用例 |
| --- | --- | --- |
| 范围、基础权限、脱敏、NGR、去重、零值已有答案 | 当前正文§3—§5 | C01—C03更新预期，C02/C03 NOT_RUN |
| GGR/时间、转代理、更新窗口收窄 | §4、G4/G5、§5.6/§6 | C01/C07；Q-03—Q-05 |
| 停佣金、列表默认/筛选、90天暂定 | §3、§5.3/G6及原型 | C04/C06/C08；Q-06—Q-08 |
| 补全导出、管理维度/联动验收 | G7、§5.4—§5.6 | C04/C05 |

证据检查为UNREVIEWED；保留未读范围，不伪造hash以通过检查。历史：09-18建立初版；09-23问题拆分；09-25仅用例格式迁移。上述旧“0评论/范围未定义”是当时读取结果，已由本轮刷新替代。所有业务用例仍未执行，无PASS。
