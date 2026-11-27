# ISOP-2092：证据同步记录

[设计](design.md) · [问题与决定](questions.md) · [测试用例](test-cases.md) · [总用例](cases.csv)

2026-11-27退出09-25—29历史测试、逐点报告及对账记录。来源读取与正式规则继续保留。

## 来源基线

2026-09-18依据本会话已读取来源整理；本次落地未重新刷新远端。J正文/0评论及[Confluence仪表板](https://alibaba-international.atlassian.net/wiki/spaces/bZaHTt6TIllW/pages/365232143) v8正文已读；Confluence评论未读。

详细来源读取边界见[本日评审](../../records-through-20261005/review-after-2072-20260918.md)。Jira状态仅为日期快照，不是本轮执行结果。

[Jira ISOP-2092](https://alibaba-international.atlassian.net/browse/ISOP-2092)

## 来源补读与同步

- 09-25及09-28重读2092与2131—2133正文及返回评论（各0）、TLSQ-78正文及评论16500（1/1）、Confluence v8正文及返回页脚／行内评论（各0）。TLSQ布局附件未独立视觉核，精确部署版本未取。
- 09-26复查接口文档 `c3cf68d`，重新读取2092及三子任务正文／评论。MySQL作为独立源单，Doris为报表加工来源，两个数据面分别验证。
- 09-28按用户指定原型核默认日期。旧原型注册率及余额字段不覆盖09-22 Jira变更。更新Q-01及C04；相关数据计算和截断答复在问题文件归口。
- 09-29根据用户决定以Completed会员提交、首充同日且 `gt>1` 核复充金额，使用 `fb_deposits.amount` 核充值。总派彩按全部类型投注额加玩家净盈利回推并计入JP，保留避免重复计入的源字段核验。原生导出步骤已归入[UI执行手册](../../../../ui/README.md#export-save)。
- 10-03用户修正总GGR为真实GGR减JP派彩，并要求分类独立计算。同步Q-04、AC-07、C07，物理源字段仍需核对。

本目录证据基线为UNREVIEWED。用例设计、有效规则和未读范围以本目录资料为准，未建立统一API执行资产。
