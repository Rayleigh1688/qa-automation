# ISOP-2092：Jira BUG试提与通知接入（2026-09-27）

2026-10-05证据退出：本文引用的非2100静态测试结果已按用户授权清理，日期结论保留为当时记录，不代表当前实测；范围见[整理记录](../../../../docs/project-cleanup-2026-10-05.md)。

[逐点执行清单](execution-20260926.md) · [实测记录](verification-20260926.md)

## 当前状态（2026-09-28）

已完成TEST-3175试提、3176—3179四张批次及一条开发汇总通知；人员映射已由用户确认。回归规则已更新为QA优先、空QA才按报告人，用户提供的三条真实消息已验证QA优先正文与送达；提及实体及其他分支仍待验证。3176/3178/3179回归通过，3177触发保存已验证但原两组完整导出及CSV内容问题仍待处理，见[最新回归](verification-20260928.md)。通用提交器尚未适配TEST/QA。

以下按操作时间保留过程记录，其中“待映射”“下一步”和未验证范围均指当时状态；最新结论以上述状态及回归记录为准。

## 第一阶段：单张BUG试提已完成

用户授权用2092的明确错误，在Filbet - Test创建一张标准BUG；参考ISOP-2089已有TEST缺陷与ISOP工作任务的跨项目关联。

| 项目 | 本次结果 |
| --- | --- |
| BUG | [TEST-3175：会员余额月趋势累加每日余额，未取期末余额](https://alibaba-international.atlassian.net/browse/TEST-3175) |
| 目标项目/类型 | Filbet - Test（TEST）/ 缺陷（10045） |
| 指派 | FE Wadewen，按前端任务ISOP-2132的当前负责人 |
| 关联 | Relates关联ISOP-2092需求和ISOP-2132前端任务；非跨项目子任务 |
| 优先级/状态 | 高 / 待办；创建后回读确认 |
| 用例 | ISOP-2092-C04-15 / F09 |
| 证据 | 09-26 FAT既有实测；09-27未重跑业务，部署版本未提供 |
| 附件 | monthly-balance-tooltip.png（24100，截图悬浮9月）、balance-month-evidence.json（24101，56个日余额及两个月重算） |
| 描述 | 问题概述、可复现步骤、需求依据、预期/实际对照、前端定位依据与影响、附件说明 |

创建前检查了2092关联缺陷及余额相关TEST搜索结果，未发现同问题；创建后已回读确认项目、指派、两条关联与两个附件。月图数据来自每日余额的前端聚合，不把MySQL源表空值当Doris统计证据。截图已经人工查看，附件只包含所需汇总值，无token、账号或会员明细。此处“人工查看”指助手视觉检查，不登记为用户人工用例PASS。

截至09-27单张试提时，其余失败尚未建单，未发送试提群消息，未将BUG改为已解决来触发通知；09-28批次见下文。

## 第二阶段：已检查现有通知，待人员映射

用户提供的[自动化规则“Jira提醒”](https://alibaba-international.atlassian.net/jira/core/projects/TEST/settings/automation#/rule/01a0a3c5-b5d3-7cca-96ab-83a2a58aba7b)已通过Chrome只读核查：

- 已启用；工作项转换至“已解决”触发。
- 类型等于“缺陷”，报告人属于达文西、ukr、雷利。
- 动作已经是Telegram sendMessage，正文含单号、标题、状态、负责人、报告人、链接。
- 当前负责人和报告人使用displayName纯文本，没有Telegram提及。
- 本轮未修改或保存线上规则。机器人凭据不落入文档或提交。

下一步以Jira accountId为稳定键映射Telegram数字user ID，并为名称做消息格式转义；不能按同名猜测用户身份。用户表示稍后查询映射。需要明确通知中的开发负责人、报告人/回归测试人员对应身份，再验证一次消息的真实提及效果。不要通过假装业务修复或切换真实BUG状态进行通知测试。

## 第三阶段：完成前两阶段后再接批量

用户最新约定优先于旧流程说明：需求规则已确认、测试报告经用户检查之后，按需求明确选定BUG，批量在TEST创建、按H5/APP/后端等责任分工指派，关联ISOP需求和相关开发任务。整批完成后只发一份按负责人分组的通知，各人只提及一次，列出对应BUG链接。失败/部分完成保留已创建编号，重试前对账，不能整批重复创建或提前宣告完成。

现有scripts/qa_delivery/connectors.py已具备提单、关联、去重状态与批次摘要基础，但create/find默认使用Story项目，本地类型仍配置为10676；不能直接拿旧submit创建本次TEST缺陷。当前通知只提及测试负责人，也缺少开发映射。待第二阶段完成再扩展现有能力，避免另建重复工具或提前启用批量提单。本轮没有更改旧组件、运行批量提交或启用常驻服务。

## BUG描述格式调整

2026-09-27用户认可格式，要求删除“环境与证据时间”整段，其余全部保留。已仅删除TEST-3175对应标题与列表，使用ADF保留其余原始格式，回读确认其余描述、标题、负责人、状态、关联与附件均未改变。后续BUG描述沿用这一精简结构；原始环境、日期与用例对应仍保存在本地执行记录中。

## 2026-09-27 TEST-3175定向提及已配置

用户授权先针对TEST-3175：状态转为已解决时在现有测试群提及雷利。已复用本地config/telegram/local.json中Rayleigh数字ID，修改现有“Jira提醒”的sendMessage正文并保存，页面显示“您的流已更新”。

- 使用issue.key条件分支：TEST-3175的消息前加“雷利，请回归验证。”，使用Telegram entities的text_link，offset=0、length=2，链接绑定雷利数字ID；其余工作项发送原消息。
- 保留原触发条件、目标测试群和单次Web请求，不另加一条通知。报告人回读为雷利，符合原有报告人筛选。
- TEST-3175回读仍为待办；未变更状态、未发测试消息。配置保存已验证，实际已解决事件触发、Telegram送达和客户端提醒效果尚待验证；不称为第二阶段端到端完成。
- 未扩展到其他测试或开发人员；后续按实际验证结果再推广映射。

实现依据：[Atlassian条件智能值](https://support.atlassian.com/cloud-automation/docs/jira-smart-values-conditional-logic/)、[Telegram消息实体与用户提及](https://core.telegram.org/bots/api#formatting-options)。机器人凭据未写入项目资料。

## 2026-09-27按报告人映射（替代3175定向配置）

用户纠正：应根据BUG报告人匹配Telegram身份，不按BUG号固定提及雷利。已用本地登记的Jira邮箱查询核实达文西、ukr、雷利三名用户的accountId，并写回忽略文件config/telegram/local.json的testers.*.jira_account_id。

线上“Jira提醒”的消息分支已改为issue.reporter.accountId匹配三人各自数字Telegram ID，移除TEST-3175条件；每次只生成对应报告人的单条提及消息。未知映射分支保留普通姓名通知，不默认提及雷利。原触发器仍只接受这三名报告人，因此新增人员时须同时补映射与报告人筛选；不会自动扩展到所有报告人。负责人字段仍展示开发负责人，不作为本次回归通知的提及依据。

保存状态见当前交接；本次未切换BUG状态或向群发送测试消息，真实触发与提及送达仍待验证。


## 2026-09-28四张BUG批次与提测群汇总

用户明确授权先用2092创建两个前端、两个后端BUG，并在整批完成后提及开发负责人；本轮不修改Jira自动化。建单前重新读取2092及2131—2133，按开发子任务负责人指派，QA按2133负责人ukr填写；未使用Story的产品负责人代替开发人员。TEST的新QA字段customfield_10334当前为必填、多用户字段，本批均只填ukr。创建前查询2092关联/文本命中的TEST缺陷，仅发现既有3175，未重复创建余额月图BUG。

| BUG | 问题 / 测试点 | 负责人 | QA | 开发任务 |
| --- | --- | --- | --- | --- |
| [TEST-3176](https://alibaba-international.atlassian.net/browse/TEST-3176) | F10 / C08-04：月趋势投充比取每日比率平均 | FE Wadewen | ukr | ISOP-2132 |
| [TEST-3177](https://alibaba-international.atlassian.net/browse/TEST-3177) | F11 / C04-17：Export点击无请求、下载或反馈 | FE Wadewen | ukr | ISOP-2132 |
| [TEST-3178](https://alibaba-international.atlassian.net/browse/TEST-3178) | F04 / C07-04：8月总GGR与分类合计相差0.20 | Bali | ukr | ISOP-2131 |
| [TEST-3179](https://alibaba-international.atlassian.net/browse/TEST-3179) | F07 / C08-03：明细投充比分子使用总投注 | Bali | ukr | ISOP-2131 |

四张均在TEST创建为缺陷、状态待办，Relates关联2092及对应开发任务；描述沿用用户批准的精简结构。3176/3179各附一份JSON和投充比截图，3177/3178各附一份JSON，共6个附件（24105—24110）。附件和复算沿用09-26实测，不宣称09-28重跑业务；3177无截图附件，仅附两轮导出交互证据摘要。证据摘要没有凭据或会员明细。上传中网络中断后先读取现有附件再补传，未重复创建BUG。

创建、指派、QA、关联、附件已逐单回读确认。随后向filbet提测发布群发送唯一一条汇总，消息ID 8610，按前端/后端分组；Telegram返回的text_mention分别绑定Wadewen与Bali的已确认数字ID，每人一次。已验证平台返回送达与提及实体，未宣称收件人已阅读或客户端一定弹出通知。未改变任何BUG状态来测试回归通知。

本地忽略目录reports/qa/ISOP-2092/20260928-jira-batch/保存四份脱敏证据、jira-receipt.json、telegram-intent.json与telegram-receipt.json；不提交人员映射、消息原始记录或凭据。既有通用提交器尚未改为TEST/QA流程，本次使用定向调用完成授权批次，不代表通用自动化已部署。

下一步优化“已解决”回归通知：优先读取QA并匹配Telegram身份，历史单QA为空时按报告人兜底；QA有人但缺少映射时须明确提示映射缺失，不误认为报告人负责。QA支持多人，需去重提及；旧规则的三报告人过滤也应一并检查，避免自动账号创建的BUG被过滤。本轮未修改该规则，端到端回归通知验证仍待完成。

本轮本地验证：`npm run check:docs`通过（230份文档），`git diff --check`通过。仅更新交付记录，未运行全套单测或联网业务门禁；未提交或推送。

## 2026-09-28回归通知改为QA优先（已保存）

用户明确授权修改TEST现有“Jira提醒”规则。通过Chrome编辑原规则，保留“工作项转换至已解决”及类型“缺陷”，删除原有报告人必须属于三名测试的条件，避免自动账号创建且QA明确的BUG被提前过滤。

原sendMessage动作仍只发一条到既有测试群。正文使用customfield_10334.size.gt(0)选择互斥分支：QA非空时迭代distinct用户，按accountId映射达文西、ukr、雷利并通过HTML的tg://user?id链接提及；QA为空时才匹配报告人。未映射人员展示姓名及“未配置Telegram映射”，不转而错误提及报告人。消息标明依据QA或报告人，保留单号、标题、状态、负责人、报告人、链接；使用HTML编码处理动态显示字段、外层jsonEncode处理完整正文，关闭链接预览。

页面确认“您的流已更新”，Save恢复禁用，触发卡片仅剩缺陷条件；规则保持启用。此验证证明配置已保存，不等于Jira智能值已实际渲染或Telegram真实送达。未修改真实BUG状态、未发送模拟已解决通知；QA单人/多人/空值及缺失映射的真实事件验证仍待完成。新建3176—3179的QA均为ukr，按新配置应提醒ukr而不是报告人雷利。

语法依据：[列表与distinct](https://support.atlassian.com/cloud-automation/docs/jira-smart-values-lists/)、[条件逻辑](https://support.atlassian.com/cloud-automation/docs/jira-smart-values-conditional-logic/)、[HTML与JSON编码](https://support.atlassian.com/cloud-automation/docs/jira-smart-values-text-fields/)。没有将机器人URL或token写入项目文档。后续增加测试人员须补映射，无需再增加报告人过滤。
