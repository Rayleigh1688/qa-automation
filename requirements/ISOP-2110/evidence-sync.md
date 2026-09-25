# ISOP-2110：证据同步记录

[设计](design.md) · [问题与决定](questions.md) · [测试用例](test-cases.md) · [总用例](cases.csv) · [来源同步](evidence-sync.md)

## 来源基线

2026-09-18依据本会话已读取来源整理；本次落地未重新刷新远端。J正文/0评论及[E-KYC](https://alibaba-international.atlassian.net/wiki/spaces/bZaHTt6TIllW/pages/293928974/E-KYC) §7.2已核，图片/Confluence评论未核。

详细来源读取边界见[本日评审](../review-after-2072-20260918.md)。Jira状态仅为日期快照，不是本轮执行结果。

[Jira ISOP-2110](https://alibaba-international.atlassian.net/browse/ISOP-2110)

## 本次落实

| 变更 | 来源与性质 | 落地位置 | 验证边界 |
| --- | --- | --- | --- |
| S01 | J正文；E-KYC §7.2 | AC-01 / ISOP-2110-C01；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；OUT_OF_SCOPE，无业务执行 |
| S02 | J正文；E-KYC §7.2 | AC-02 / ISOP-2110-C02；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；OUT_OF_SCOPE，无业务执行 |
| S03 | J正文；E-KYC §7.2 | AC-03 / ISOP-2110-C03；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；OUT_OF_SCOPE，无业务执行 |

## 未完成

上述未读素材与待确认问题仍保留；未建立远端完整同步或自动执行就绪结论。本目录尚未登记机器hash基线，证据检查应显示UNREVIEWED，而不是伪造完整已审阅。收到新决定/补读来源后逐项更新再登记。

## 2026-09-23问题写法调整

Q-01以已有决定展示；用户此前指定本单不再测、E-KYC略过的决定保留，全部用例继续OUT_OF_SCOPE。当前没有新增待答问题，上方未读素材仍未补读。

首屏改为短名称索引，详情按场景、问题点、需要确认展开，来源和用例关联后置；已确认项保留决定。此次仅整理现有证据，未取得新业务答复、未刷新远端、未补读缺失素材或执行业务测试；原有执行状态和机器证据未登记状态保留。

## 2026-09-25用例格式统一

按用户确认的2092新版，将本需求3条用例由宽表展开为“总览＋详情卡片”，前置条件和预期逐项列出、操作编号、待确认链接原问题，验收关联及实现说明后置。原编号、场景、业务内容、AC关联、验证方式、状态和负责人保留，同步生成cases.csv；已有执行边界和历史结果保持原记录。本次仅格式整理，未刷新远端来源、取得新业务决定或执行业务API/UI，机器证据基线仍未登记。
