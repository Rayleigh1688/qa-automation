# ISOP-2103：免费旋转派发弹窗测试设计

[设计](design.md) · [问题](questions.md) · [测试重点](test-cases.md) · [W26评审](../reviews/2026W26-20261006.md)

五个影响活动已列明，奖励类型与交互规则由[问题文档](questions.md)维护；不能仅凭活动名判定全部奖励为免费旋转。来源读取日期为2026-10-06。本次仅按最终W26评审迁移到任务单目录，未刷新远端来源、未重新测试；已确认规则、待确认决定及历史交付陈述分开记录。

## 已明确范围

- 活动清单为First 3 deposits、Daily accumulated deposit、KYC Free Spin、输值返利及厂商排行榜。
- 共用Lark为充值／彩金金额动效基线，没有提供逐活动免费旋转契约；金币金额动效不能直接作为旋转次数及领取流程的预期。
- ISOP-2103评论17489于2026-09-28称App已提测。该陈述不代表H5、后端及五活动都完成，更不是本轮PASS。
- 共用通知枚举不自动决定产品范围。2120的选片与本单有交叉影响，但现金返利、免费旋转和代币必须按最终奖励映射分别判断。

## 来源读取边界

2026-10-06已读Jira正文及全部相关评论、子任务，已读共享Lark正文、短评论和白板概览；白板小字未逐项放大。Lark页面更新时间仅显示08-19（页面未显示年份）。

该Lark的通用金额动效不能替代免费旋转专门交互；已读来源与未决规则分开，不因共用文档就扩大本单奖励范围。真实奖励类型、触发时点及交互决定只在questions.md记录。

## 测试准备与执行边界

当前端、构建、活动配置及隔离样本属于执行准备，缺少样本不直接判产品缺陷。实际发放与消息须关联，不能以达到条件或创建记录直接登记成功。

当前目录只保留设计资产，没有自动执行计划；不恢复历史目录执行，不为补覆盖重复发放奖励。

## 规则决定入口

- [Q-01：五活动奖励与消息映射](questions.md#q-01)。
- [Q-02：代币与厂商活动范围](questions.md#q-02)。
- [Q-03：弹出时点与旋转交互](questions.md#q-03)。

## 来源

| 来源 | 定位与读取范围 |
| --- | --- |
| Jira正文 | [ISOP-2103](https://alibaba-international.atlassian.net/browse/ISOP-2103)，五活动清单；读取2026-10-06 |
| App提测陈述 | [评论17489](https://alibaba-international.atlassian.net/browse/ISOP-2103?focusedCommentId=17489)，2026-09-28App提测；读取2026-10-06 |
| 共享说明 | [金额动效Lark](https://qsgpn7a1512s.sg.larksuite.com/wiki/UU0Sw9J5GiSJBukGkR5l6hLWgDe)，通用金额动效；读取2026-10-06 |
| 通知基础设施背景 | [2168评论17452](https://alibaba-international.atlassian.net/browse/ISOP-2168?focusedCommentId=17452)，ty=3／4及sub_ty=39；不直接定义本单产品范围 |
| 最终评审 | [W26免费旋转评审](../reviews/2026W26-20261006.md#isop-2103免费旋转派发弹窗)，本次迁移依据 |

## 历史日期资料

[10-05旧版资料](../history/archived-20261005/snapshots/ISOP-2103/design.md) · [旧问题与决定](../history/archived-20261005/snapshots/ISOP-2103/questions.md)。旧规则、问题状态与用例保留为日期快照，不自动作为W26预期；当前问题答复只维护在本单文件。
