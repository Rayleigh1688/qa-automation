# ISOP-2092：证据同步记录

[设计](design.md) · [问题与决定](questions.md) · [测试用例](test-cases.md) · [总用例](cases.csv) · [来源同步](evidence-sync.md)

## 来源基线

2026-09-18依据本会话已读取来源整理；本次落地未重新刷新远端。J正文/0评论及[Confluence仪表板](https://alibaba-international.atlassian.net/wiki/spaces/bZaHTt6TIllW/pages/365232143) v8正文已读；Confluence评论未读。

详细来源读取边界见[本日评审](../review-after-2072-20260918.md)。Jira状态仅为日期快照，不是本轮执行结果。

[Jira ISOP-2092](https://alibaba-international.atlassian.net/browse/ISOP-2092)

## 本次落实

2026-09-26按用户要求，以C01—C08为索引将既有证据拆入[逐点执行清单](execution-20260926.md)，逐项登记结果、执行进度、实际执行人及后续处理方；同步本地HTML和逐点CSV/JSON。失败与未执行分开，需开发/产品处理与用户可选人工视觉验收分开。仅离线整理，未新增业务执行或规则答复，未改变原8条兼容场景状态及机器基线。

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

## 2026-09-25辅助资料分析与FAT首轮实测

用户指定TLSQ-78辅助分析并授权2092功能测试及必要读写；随后明确使用现有登录API/脚本和账号，无需人工登录。已刷新2092/2131—2133正文与全部返回评论、TLSQ-78正文及评论16500（1/1）、Confluence v8正文和页脚/行内评论（各0）；TLSQ布局附件未独立视觉复核，接口文档仅核本地c3cf68d，精确部署版本未取得，故机器基线仍UNREVIEWED。

[本轮分析及证据](verification-20260925.md)记录辅助规则适用边界及实际执行。同步C01的新版字段/零值断言、C06的已明确跨日人数规则、C07的bet_type/JP依据，以及Q-03—Q-05已有答案。C01/C03/C06/C07按失败回填FAIL，其余保留未覆盖/阻塞；负责人仍未重新分派。原始API、UI日期/页面及只读SQL留独立忽略批次，无历史失败改判、Jira写入或群消息。用户虽授权必要读写，已有记录已能复现问题，本轮未新增资金或配置写入。

## 2026-09-26三个月数据与全面UI/API

用户要求先按实际数据分析，暂不查看待确认项；随后明确全面验证UI/API，并说明首页统计来自Doris，当前MySQL仅能重算源单。本轮恢复图表/下钻/导出范围。已fetch接口文档，HEAD与origin/main同为c3cf68d；重新读取2092及2131—2133正文/评论（均0），TLSQ/Confluence沿用09-25快照，精确部署版本与附件视觉范围仍未补。机器基线保持UNREVIEWED。

[本轮证据与结论](verification-20260926.md)记录三组累计、87日、29项图表、卡片下钻和源单重算。C04/C08由BLOCKED改为FAIL，其余已有失败保留；C02/C05标明部分完成边界。同步设计中真实接口映射及用例图表执行范围，问题只登记最新执行决定，不关闭待答项。现有样本足够，未运行P0造数；导出ty=1受理、ty=2锁失败后停止，未取得文件。未写业务资金/KYC/配置、未建BUG或发消息。

09-26结果澄清：依据同批证据回填Q-01—Q-06已核实子项，保留目标规则冲突/gt=0/源单差额/舍入边界；同步C05/C07前置描述。补充12组已通过检查及证据索引，HTML将C02/C05展示为部分完成，原始JSON/CSV的场景结果不改。仅离线复核，无新增业务执行或产品答复。

## 2026-09-26零百分比展示纠正

用户明确比例可以保留小数。核对本批jira-snapshot.json中2092完整正文，未发现零百分比禁止保留小数的规定；旧“整数0”来源为09-25用户补充，扩大到比率缺乏依据。当前C01-04/F01仅保留零金额格式失败，0.00%移出失败范围；同步设计、Q-06、用例、逐点清单及报告，原始截图/响应不改，旧批次报告保留历史含义。零分母应取0还是空值仍是独立问题。未新增业务运行。
