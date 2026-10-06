# ISOP-2120：金币派发效果二期测试设计

[设计](design.md) · [问题](questions.md) · [测试重点](test-cases.md) · [W26评审](../reviews/2026W26-20261006.md)

本期新增升级礼金与生日礼金，旧事件选片边界已明确；通知契约和展示去重决定在[问题文档](questions.md)维护。来源读取日期为2026-10-06。本次仅按最终W26评审迁移到任务单目录，未刷新远端来源、未重新测试；已确认规则、待确认决定及历史交付陈述分开记录。

## 已明确规则

- 只新增两类礼金效果：升级礼金文案为`Congratulation! You received Level Up Bonus!`，生日礼金为`Congratulation! You received Birthday Bonus!`。
- ISOP-2168评论17433明确：`top_up/daily_reward/cash_rebate`仍用版本3 SBS，`level_up/birthday`用旋转币SBS。不要求所有入账事件统一换片。
- ISOP-2168评论17452的`ty=3`免费旋转／`num`、`ty=4`代币／`token`和`sub_ty=39`厂商活动属于通知基础设施，不是本单新增产品范围。
- 共享金额动效Lark提供充值／彩金通用基线；充值延迟且玩家已入游戏，回首页只弹窗、不滚动金额。该路径按本期实际影响回归，不新增充值计算验收。

## 素材与读取边界

附件24054已查看：3秒预览与RGB／Alpha并排交付片，代表帧有金币、彩带及吉祥物。预览的充值文案、`+10`和Skip属于素材样例，不作为两类礼金的金额或文案预期。素材视觉检查不证明H5／App已经正确合成或响应实际奖励事件。

共享Lark正文、两条短评论和白板概览已读，白板小字未逐项放大；页面更新时间仅显示08-19（页面未显示年份）。通用金额动效不替代两类礼金当前消息契约，也不替代免费旋转的专门交互。

## 交付陈述与执行边界

2026-09-23的SIT部署与2026-09-28的App前端完成是历史来源陈述，不作为当前构建或端到端通过证据。2026-09-25“等待契约”也不能直接作为当前状态。

后续测试需提供当前H5／App构建、后端ISOP-2140最终契约及隔离样本；仅收到消息不等于奖励实际到账。当前目录没有正式执行计划，不恢复历史目录执行，不重放真实礼金发放。

## 规则决定入口

- [Q-01：礼金通知与发放契约](questions.md#q-01)。
- [Q-02：礼金重复与连续展示](questions.md#q-02)。

未决内容与答复只在questions.md维护，测试重点引用问题编号。

## 来源

| 来源 | 定位与读取范围 |
| --- | --- |
| Jira正文 | [ISOP-2120](https://alibaba-international.atlassian.net/browse/ISOP-2120)，本期两类礼金及文案；读取2026-10-06 |
| H5补充 | [评论17433](https://alibaba-international.atlassian.net/browse/ISOP-2168?focusedCommentId=17433)及[17452](https://alibaba-international.atlassian.net/browse/ISOP-2168?focusedCommentId=17452)，选片和通知基础设施范围；读取2026-10-06 |
| App交付陈述 | [评论17488](https://alibaba-international.atlassian.net/browse/ISOP-2167?focusedCommentId=17488)，2026-09-28前端完成；读取2026-10-06 |
| 共享说明 | [金额动效Lark](https://qsgpn7a1512s.sg.larksuite.com/wiki/UU0Sw9J5GiSJBukGkR5l6hLWgDe)，正文、短评论及白板概览；读取2026-10-06 |
| 动画附件 | Jira附件24054，已核归档、视频metadata及少量代表帧；不是客户端效果实测 |
| 最终评审 | [W26金币二期评审](../reviews/2026W26-20261006.md#isop-2120金币派发效果二期)，本次迁移依据；不采用分组工作稿的旧问题数 |

## 历史日期资料

[10-05旧版资料](../history/archived-20261005/snapshots/ISOP-2120/design.md) · [旧问题与决定](../history/archived-20261005/snapshots/ISOP-2120/questions.md)。旧规则、问题状态与用例保留为日期快照，不自动作为W26预期；当前问题答复只维护在本单文件。
