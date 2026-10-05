# ISOP-2092：2026-09-29 Jira 缺陷交付

2026-10-05证据退出：本文引用的非2100静态测试结果已按用户授权清理，日期结论保留为当时记录，不代表当前实测；范围见[整理记录](../../../../docs/project-cleanup-2026-10-05.md)。

> 最新派彩结论：09-29按用户新SQL补核总派彩：站点0、主表非体育加体育专表，全部bet_type；8月实时DB与31日报及月报完全对平，总额585207.335。09-16原差额由体育来源替换解释，09-15/22/25差额仍待核。详见[来源复核](verification-20260929-payout-review.md)。原89日主表检查属于旧口径，未按新口径重跑全部89日。

最新测试报告（原文件已退出，历史路径：`../../../../reports/qa/ISOP-2092/20260929-full/results.html`） · [复测记录](verification-20260929-full.md) · [此前交付](bug-delivery-20260927.md)

本批创建11张缺陷，随后用户核定复充金额gt>1，TEST-3201撤回并转已完成。当前保留9张有效新缺陷及既有TEST-3175（TEST-3204随后因amount字段口径更正撤回）；待核验及用户排除的场景未作为已确认BUG提交。

## 本批单据（含已撤回记录）

| Jira | 问题 | 检查点 | 负责人 |
| --- | --- | --- | --- |
| [TEST-3194](https://alibaba-international.atlassian.net/browse/TEST-3194) | 首页登录人数错别字及总派彩提示含多余“此次调整” | TEXT01, TEXT02 | FE Wadewen |
| [TEST-3195](https://alibaba-international.atlassian.net/browse/TEST-3195) | 金额、人均、比例未按截断两位展示，零值格式不统一 | UI03, UI15 | FE Wadewen |
| [TEST-3196](https://alibaba-international.atlassian.net/browse/TEST-3196) | 首页自定义查询允许90天，未执行小于90天限制 | UI09 | Bali |
| [TEST-3197](https://alibaba-international.atlassian.net/browse/TEST-3197) | 两天查询仍返回人均及登录投注人数，未隐藏跨日指标 | UI10 | Bali |
| [TEST-3198](https://alibaba-international.atlassian.net/browse/TEST-3198) | 会员余额在下钻明细中缺失且CSV未导出该列 | UI11, EX04 | Bali |
| [TEST-3199](https://alibaba-international.atlassian.net/browse/TEST-3199) | ARPU和人均充值月图累加每日人均，展示无意义跨日值 | UI13 | FE Wadewen |
| [TEST-3200](https://alibaba-international.atlassian.net/browse/TEST-3200) | 投注CSV表头列数错位、单位错误且投充比仍使用总投注 | EX02, EX03 | Bali |
| [TEST-3201](https://alibaba-international.atlassian.net/browse/TEST-3201) | 已撤回：金额gt>1，旧gt=0漏计结论不成立 | SRC01 | Bali |
| [TEST-3202](https://alibaba-international.atlassian.net/browse/TEST-3202) | 投注、有效投注及GGR与已结算源注单存在多日差额 | SRC03 | Bali |
| [TEST-3203](https://alibaba-international.atlassian.net/browse/TEST-3203) | 总派彩源差额（原提单4日，09-16已对平，剩3日；Jira尚未同步） | SRC05 | Bali |
| [TEST-3204](https://alibaba-international.atlassian.net/browse/TEST-3204) | 已撤回：充值使用amount，1600与报表一致 | SRC04 | Bali |

全部为TEST/缺陷，QA均为ukr；除TEST-3201已撤回并转已完成外，其余10张新单均待办；关联ISOP-2092和当前负责人对应的ISOP-2132前端或ISOP-2131后端任务。11份脱敏JSON证据及1份真实投注CSV已上传。描述沿用用户确认的结构，不新增“环境与证据时间”章节。跨前后端项以已观察API/导出证据选主要负责人，说明中保留联调范围。

## 既有缺陷与未提范围

- [TEST-3175](https://alibaba-international.atlassian.net/browse/TEST-3175)：余额周/月累加仍失败，新增回归评论17492，状态保持待办，不重复创建。
- TEST-3176—3179原范围本轮通过，已有已完成状态保持；新CSV内容问题与原下载触发、页面投充比问题分开。
- 复充金额最终gt>1，仍限定Completed、会员提交、首充当天。89日证据离线复评对平；TEST-3201标题和描述注明撤回，评论17493说明无需修复。原gt!=1提单依据及gt=0漏计结论作废，附件保留历史。
- 默认六个月完整性与180天协调、登录日志最早3日缺源保留待核；月初/跨年按用户要求未测。

## 验证与边界

创建前查重仅命中既有3175—3179；网络中断后先读取现有编号、关联和附件再恢复，没有整批重提。通过Jira独立回读核对全部11张的标题、负责人、QA、两条关联和12个附件，3175评论也已回读。原始创建回执、提交包、脱敏证据和独立回读在本机忽略目录`reports/qa/ISOP-2092/20260929-jira-batch/`。

本次是基于09-29实测证据的提单交付，未重新执行业务API/UI、资金写入或数据库写入；TEST-3201按撤回转已完成，其余BUG状态未改；群提醒见下文。通用提交器的TEST/QA适配仍未部署，本次复用现有连接器与Atlassian Rovo定向完成授权批次。

## 本批群提醒（提单后用户明确授权）

已向filbet提测发布群发送唯一一条提醒，消息ID 8655。前端3张新BUG、后端7张新BUG按当前Jira负责人分组；FE Wadewen与Bali各提及一次。另说明TEST-3175回归仍失败，TEST-3201按gt>1金额口径撤回，无需修复。Telegram成功返回消息及两名开发的text_mention实体，未宣称收件人已读；没有重复发送或改变Jira状态。发送前重新读取全部相关BUG，10张新BUG均待办，3201已完成。回执保存在本机忽略目录20260929-jira-batch/telegram-reminder-receipt.json。

## 充值字段更正后的撤回

用户确认充值金额取amount，不是paid_amount。89日现有证据离线复评对平，TEST-3204标题/描述注明旧结论作废，评论17495并转已完成；读取时该单已由他人转为已解决，本次不宣称代码修复回归。原创建附件和通知记录保留历史，当前有效新BUG为9张；本次未发送群消息。
