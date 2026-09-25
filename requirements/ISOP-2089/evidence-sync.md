# ISOP-2089：证据同步记录

[设计](design.md) · [问题与决定](questions.md) · [测试用例](test-cases.md) · [总用例](cases.csv) · [来源同步](evidence-sync.md)

## 来源基线

2026-09-18依据本会话已读取来源整理；本次落地未重新刷新远端。J正文/0评论，附件23972已视觉核对，含默认、输入、结果、分类、无结果。

详细来源读取边界见[本日评审](../review-after-2072-20260918.md)。Jira状态仅为日期快照，不是本轮执行结果。

[Jira ISOP-2089](https://alibaba-international.atlassian.net/browse/ISOP-2089)

## 本次落实

| 变更 | 来源与性质 | 落地位置 | 验证边界 |
| --- | --- | --- | --- |
| S01 | J附件23972 | AC-01 / ISOP-2089-C01；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；NOT_RUN，无业务执行 |
| S02 | J附件23972；尚需Q-02 | AC-02 / ISOP-2089-C02；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；BLOCKED，无业务执行 |
| S03 | J附件23972 | AC-03 / ISOP-2089-C03；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；NOT_RUN，无业务执行 |
| S04 | J附件23972；当时尚需Q-01 | AC-04 / ISOP-2089-C04；design.md、questions.md、test-cases.md、生成cases.csv | 历史设计同步记录；Trending规则后续已由用户补充，当前用例NOT_RUN，无业务执行 |
| S05 | J附件23972；尚需Q-02 | AC-05 / ISOP-2089-C05；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；BLOCKED，无业务执行 |
| S06 | 2026-09-21用户补充 | AC-04 / ISOP-2089-C04；design.md、questions.md、test-cases.md、cases.csv | Trending Games规则已同步；NOT_RUN，Filbet Ranking数据、合规字段和进入游戏契约仍待核对 |
| S07 | 2026-09-21用户补充 | AC-04 / ISOP-2089-C04；design.md、questions.md、test-cases.md、cases.csv | Recommended Games规则已同步；NOT_RUN，推荐权重、合规字段和进入游戏契约仍待核对 |
| S08 | 2026-09-21用户补充 | AC-01、AC-02、AC-05 / ISOP-2089-C01、C02、C05；design.md、questions.md、test-cases.md、cases.csv | 搜索框交互规则已同步；NOT_RUN，匹配算法、分类空集及清空后的页面状态仍待核对 |

## 未完成

上述未读素材与待确认问题仍保留；未建立远端完整同步或自动执行就绪结论。本目录尚未登记机器hash基线，证据检查应显示UNREVIEWED，而不是伪造完整已审阅。收到新决定/补读来源后逐项更新再登记。

## 2026-09-23问题写法整理

保留Q-01已解决及Q-02部分解决；原Q-02的分类空集、清空后状态拆为Q-03、Q-04。设计及C02/C05依赖同步，CSV重新生成；已确认推荐规则保留。问题改为简短名称、场景、问题点和所需答复，来源及用例关联后置。仅沿用本地已有来源，未重新读取远端、未收到新业务决定、未执行业务测试；原用例状态与未读范围保留，机器证据基线仍未登记。

## 2026-09-25用例格式统一

按用户确认的2092新版，将本需求5条用例由宽表展开为“总览＋详情卡片”，前置条件和预期逐项列出、操作编号、待确认链接原问题，验收关联及实现说明后置。原编号、场景、业务内容、AC关联、验证方式、状态和负责人保留，同步生成cases.csv；已有执行边界和历史结果保持原记录。本次仅格式整理，未刷新远端来源、取得新业务决定或执行业务API/UI，机器证据基线仍未登记。
