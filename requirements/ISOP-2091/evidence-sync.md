# ISOP-2091：证据同步记录

[设计](design.md) · [问题与决定](questions.md) · [测试用例](test-cases.md) · [总用例](cases.csv) · [来源同步](evidence-sync.md)

## 来源基线

2026-09-21重新读取Jira正文、评论区、21个附件列表和6个子任务列表。正文内Lark/Figma/后台原型链接均可见；未逐一下载附件、操作原型或展开子任务详情页。正文规则已同步，接口契约/部署/业务执行仍未核验。

详细来源读取边界见[本日评审](../review-after-2072-20260918.md)。Jira状态仅为日期快照，不是本轮执行结果。

[Jira ISOP-2091](https://alibaba-international.atlassian.net/browse/ISOP-2091)

## 本次落实

| 变更 | 来源与性质 | 落地位置 | 验证边界 |
| --- | --- | --- | --- |
| S01 | Jira正文功能概述/2.1 | AC-01/AC-02 / ISOP-2091-C01/C02；design.md、questions.md、test-cases.md、cases.csv | 规则同步；NOT_RUN，无业务执行 |
| S02 | Jira正文2.2排名 | AC-04 / ISOP-2091-C04；design.md、questions.md、test-cases.md、cases.csv | Q-01已解除；NOT_RUN，无业务执行 |
| S03 | Jira正文2.3奖励、2.4派发 | AC-05/AC-09 / ISOP-2091-C05/C09；design.md、questions.md、test-cases.md、cases.csv | Q-02已解除；NOT_RUN，无业务执行 |
| S04 | Jira正文2.5配置修改 | AC-06 / ISOP-2091-C06；design.md、questions.md、test-cases.md、cases.csv | Q-03已解除；NOT_RUN，无业务执行 |
| S05 | Jira正文3.2后台配置 | AC-03/AC-07 / ISOP-2091-C03/C07；design.md、test-cases.md、cases.csv | 原型/契约待核；NOT_RUN，无业务执行 |
| S06 | Jira正文3.3/四及附件设计 | AC-08 / ISOP-2091-C08；design.md、questions.md、test-cases.md、cases.csv | Q-04设计稿缺陷保留；BLOCKED，无业务执行 |

## 未完成

上述子任务详情、附件原图逐项视觉核验、接口契约、部署版本和业务执行仍未完成；未建立自动执行就绪结论。本目录尚未登记机器hash基线，证据检查应显示UNREVIEWED，而不是伪造完整已审阅。Q-01至Q-03已同步为正文决定，Q-04/Q-05继续保留。

## 2026-09-23问题写法整理

保留Q-01—Q-03已有答案与Q-04/Q-05待核验，先展示所需设计修订和交付资料，详细依据后置；More Games仍为建议。问题改为简短名称、场景、问题点和所需答复，来源及用例关联后置。仅沿用本地已有来源，未重新读取远端、未收到新业务决定、未执行业务测试；原用例状态与未读范围保留，机器证据基线仍未登记。
