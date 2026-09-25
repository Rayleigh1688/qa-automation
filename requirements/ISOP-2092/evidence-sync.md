# ISOP-2092：证据同步记录

[设计](design.md) · [问题与决定](questions.md) · [测试用例](test-cases.md) · [总用例](cases.csv) · [来源同步](evidence-sync.md)

## 来源基线

2026-09-18依据本会话已读取来源整理；本次落地未重新刷新远端。J正文/0评论及[Confluence仪表板](https://alibaba-international.atlassian.net/wiki/spaces/bZaHTt6TIllW/pages/365232143) v8正文已读；Confluence评论未读。

详细来源读取边界见[本日评审](../review-after-2072-20260918.md)。Jira状态仅为日期快照，不是本轮执行结果。

[Jira ISOP-2092](https://alibaba-international.atlassian.net/browse/ISOP-2092)

## 本次落实

| 变更 | 来源与性质 | 落地位置 | 验证边界 |
| --- | --- | --- | --- |
| S01 | J§二 | AC-01 / ISOP-2092-C01；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；NOT_RUN，无业务执行 |
| S02 | J§三；既有BI用户决定 | AC-02 / ISOP-2092-C02；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；NOT_RUN，无业务执行 |
| S03 | J§三 | AC-03 / ISOP-2092-C03；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；NOT_RUN，无业务执行 |
| S04 | J§四；尚需Q-01 | AC-04 / ISOP-2092-C04；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；BLOCKED，无业务执行 |
| S05 | J§二；BI Q-01；尚需Q-02 | AC-05 / ISOP-2092-C05；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；BLOCKED，无业务执行 |
| S06 | J§二；BI D-03；尚需Q-03 | AC-06 / ISOP-2092-C06；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；BLOCKED，无业务执行 |
| S07 | J§二；尚需Q-04 | AC-07 / ISOP-2092-C07；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；BLOCKED，无业务执行 |
| S08 | J§二；尚需Q-04 | AC-08 / ISOP-2092-C08；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；BLOCKED，无业务执行 |
| S09 | 2026-09-25用户补充 | AC-04 / ISOP-2092-C04；design.md、questions.md、test-cases.md、cases.csv | 已明确以当前点击日期作为快捷日期推演基准；NOT_RUN，具体起止及180天限制仍待确认 |
| S10 | 2026-09-25用户补充 | AC-05 / ISOP-2092-C05；design.md、questions.md、test-cases.md、cases.csv | 已明确首充为用户注册后的第一笔充值；后续根据TLSQ-78评论16500补齐复充口径 |
| S13 | TLSQ-78评论16500及本地首页BI规则记录 | AC-05 / ISOP-2092-C05；design.md、questions.md、test-cases.md、cases.csv | 规则已明确：首充为第一笔Completed充值（gt=1）；复充为gt!=1且首次充值时间为统计当日；历史首充用户后续充值不计入复充，多日按每日分类结果累加；NOT_RUN，字段映射待核验 |
| S11 | 2026-09-25用户补充 | AC-07、AC-08 / ISOP-2092-C07、C08；design.md、questions.md、test-cases.md、cases.csv | 已明确显示值为0时展示整数0且不显示小数点；NOT_RUN，零分母及其他舍入规则仍待核验 |
| S12 | 2026-09-25用户截图补充 | AC-07 / ISOP-2092-C07；design.md、questions.md、test-cases.md、cases.csv | 已明确总派彩包含一般注单、FS和Jackpot；使用不区分bet_type的注单回推并加上jp_winning总和，不使用net_amount回推；NOT_RUN，GGR字段及正负号仍待核验 |

## 未完成

上述未读素材与待确认问题仍保留；未建立远端完整同步或自动执行就绪结论。本目录尚未登记机器hash基线，证据检查应显示UNREVIEWED，而不是伪造完整已审阅。收到新决定/补读来源后逐项更新再登记。

## 2026-09-23问题写法整理

保留Q-01—Q-04；原Q-04的金额字段、零分母/舍入拆为Q-05、Q-06。设计及C07/C08依赖同步，CSV重新生成；既有图表执行范围不变。问题改为简短名称、场景、问题点和所需答复，来源及用例关联后置。仅沿用本地已有来源，未重新读取远端、未收到新业务决定、未执行业务测试；原用例状态与未读范围保留，机器证据基线仍未登记。

## 2026-09-25用例格式优化

按用户指定的本地参考项目QA-Automation-Sport中SK-43功能用例写法，将十列宽表改为“简短总览＋逐条前置条件、步骤、预期、待确认”，采用本仓库现有卡片协议保持CSV入口兼容。保留C01—C08、AC关联、验证方式、负责人和登记状态；补充日期边界操作、首充/复充分组计算样本、跨日去重对照及派彩/比率核对步骤。样本均为设计示例，不是环境实测。

依据为本目录已有设计、问题答复及2026-09-25补充记录，没有新增产品决定。S09、S11、S12中的NOT_RUN仅说明对应补充未执行，不能理解为已解除整条用例阻塞：C04、C07、C08仍为BLOCKED；C05按S13保持NOT_RUN。图表执行范围不变；未刷新Jira/Confluence、未建立机器基线或执行业务测试。
