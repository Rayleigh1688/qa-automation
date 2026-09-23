# ISOP-2090：证据同步记录

[设计](design.md) · [问题与决定](questions.md) · [测试用例](test-cases.md) · [总用例](cases.csv) · [来源同步](evidence-sync.md)

## 来源基线

2026-09-18依据本会话已读取来源整理；本次落地未重新刷新远端。J正文及产品评论17355（2026-09-16）已读；[Lark](https://qsgpn7a1512s.sg.larksuite.com/wiki/ITOnwma9BiT8xRktp0el1LMQgge)正文/T&C/0评论已读，Board和mock原型未核。

详细来源读取边界见[本日评审](../review-after-2072-20260918.md)。Jira状态仅为日期快照，不是本轮执行结果。

[Jira ISOP-2090](https://alibaba-international.atlassian.net/browse/ISOP-2090)

## 本次落实

| 变更 | 来源与性质 | 落地位置 | 验证边界 |
| --- | --- | --- | --- |
| S01 | J评论17355 §2/4 | AC-01 / ISOP-2090-C01；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；NOT_RUN，无业务执行 |
| S02 | J评论17355 §2 | AC-02 / ISOP-2090-C02；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；NOT_RUN，无业务执行 |
| S03 | J评论17355 §2 | AC-03 / ISOP-2090-C03；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；NOT_RUN，无业务执行 |
| S04 | J评论17355 §2 | AC-04 / ISOP-2090-C04；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；NOT_RUN，无业务执行 |
| S05 | J正文§2.3/2.4及评论17355 | AC-05 / ISOP-2090-C05；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；NOT_RUN，无业务执行 |
| S06 | J评论17355 §2 | AC-06 / ISOP-2090-C06；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；NOT_RUN，无业务执行 |
| S07 | J正文§2.2 | AC-07 / ISOP-2090-C07；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；NOT_RUN，无业务执行 |
| S08 | J正文§三/四；尚需Q-03、Q-04、Q-05 | AC-08 / ISOP-2090-C08；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；BLOCKED，无业务执行 |
| S09 | Lark T&C；J正文Step3；尚需Q-02 | AC-09 / ISOP-2090-C09；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；BLOCKED，无业务执行 |
| S10 | J正文VIP矩阵；尚需Q-04 | AC-10 / ISOP-2090-C10；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；BLOCKED，无业务执行 |
| S11 | J正文Step3；尚需Q-05 | AC-11 / ISOP-2090-C11；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；BLOCKED，无业务执行 |

## 未完成

上述未读素材与待确认问题仍保留；未建立远端完整同步或自动执行就绪结论。本目录尚未登记机器hash基线，证据检查应显示UNREVIEWED，而不是伪造完整已审阅。收到新决定/补读来源后逐项更新再登记。

## 2026-09-23问题写法整理

保留Q-01—Q-05；原Q-04拆出Q-06金额/舍入、Q-07配置生效、Q-08历史0迁移，原Q-05拆出Q-09失败重试，原Q-03拆出Q-10汇总封顶。设计及C08/C10/C11依赖同步，CSV重新生成。问题改为简短名称、场景、问题点和所需答复，来源及用例关联后置。仅沿用本地已有来源，未重新读取远端、未收到新业务决定、未执行业务测试；原用例状态与未读范围保留，机器证据基线仍未登记。
