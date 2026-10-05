# 当前交接

更新：2026-10-05。当前只推进ISOP-2100；业务结论按下列原始日期来源核对，本地检查不替代业务验收。

## 当前入口与下一步

| 用途 | 权威记录 | 本地报告 |
| --- | --- | --- |
| 本期需求范围与结论 | [需求核查](requirements/ISOP-2100/acceptance-20261005.md) | [本期报告](reports/qa/ISOP-2100/20261005-requirement-review/views/report.html) |
| 四项已提缺陷与群送达 | [BUG交付](requirements/ISOP-2100/bug-delivery-20261005.md) | [Jira回读](reports/qa/ISOP-2100/20261005-jira-delivery/verified-delivery.json) |
| 最新补测与未覆盖边界 | [10-05补测](requirements/ISOP-2100/verification-20261005-followup.md) | [补测报告](reports/qa/ISOP-2100/20261005-followup/views/report.html) |

下一步跟进四单修复，按[当前问题](requirements/ISOP-2100/questions.md#current-bugs)定向复验，并补本期页面／真实CSV验证。用例与当前报告统一从[需求入口](requirements/README.md)查阅。

## 2100当前事实与边界

- 本期按需求正文五处功能核查，结论仍有问题；10-05确认F01、F05、F08、F09。不以47条扩展细项全部完成作为本期验收门槛，也不把本轮补测说成47项全量重跑。
- 用户已授权提交并完成四单：F01→TEST-3221（补既有空描述），F05→TEST-3227，F08→TEST-3228，F09→TEST-3226。四单关联ISOP-2100及对应后端任务；10-05回读为待办／高／Bali／QA ukr，该快照不代表已修复。
- 四单汇总已发 **filbet提测发布群**，用户明确确认送达。使用`submission_chat_id`；实际只发一条，未向测试部发送。本地响应断言失败导致消息ID未保存，不补造ID、不重发。依据见[群同步记录](requirements/ISOP-2100/bug-delivery-20261005.md#提单后群同步)。
- 10-05接口及只读源对平普通外充300、外提100、有效投注1660、GGR89.74。按正文活动彩金仅排除邀请佣金，Bonus应191.47／实际2，NGR应−101.73／实际87.74；排行榜150错误归属与返利39.47遗漏分别登记，不推定共同根因。最新复评已替代“返利待核”和旧Bonus2全量口径。
- F02默认日期、F03查询上限、F04管理交付缺项、F06导出漏行最近证据为10-02，本次未复验。10-05 UI连接pipe启动失败，HTML视觉验证也未完成；不能由旧页面／CSV推断当前仍复现或已修复。
- 正文范围仍含权限／服务端脱敏、G6限制（§5.5同G6）、非零JP、成功状态排除、人数去重和GMT+8日切；样本未取得的部分不判通过或产品BUG。邀请统计全回归、舍入算法、故障页样式、指定日志／任务实现不增为本期门槛；后页`t=0`不直接报分页BUG。
- 用户确认佣金已停止；未独立验证后台停算停发运行状态，菜单隐藏不能证明后台停止。历史转代理、本期之前资金数据、PAY-01及独立代理申请审批不恢复为本期额外门槛；范围以最新需求核查为准。

## 账号、资金与运行状态

- 沿用A_kyc及既有M1／M2／M0；M0保持零活动，不重建账号、不重放充值／提现。精确身份和订单只在忽略目录，先读[资金准备](requirements/ISOP-2100/verification-20261002-priority.md)、[投注后对账](requirements/ISOP-2100/verification-20261002-post-bet.md)及[提现记录](requirements/ISOP-2100/verification-20261002-withdraw.md)。
- M2唯一提现曾HTTP200但业务false、实际落单扣款；后续只读核到completed及提款100。原创建FAIL保持，不重放创建或调用成功接口制造通过；三方实际收款按用户范围未验。数据库始终只读，业务false后停止后续成功动作。
- A_new／A_client既有身份及10-02待审申请记录留[链路记录](requirements/ISOP-2100/verification-20261002-client-closure.md)，不重新开户、重复审批、改库直接开通或改变代理总开关。用户后续确认申请／邀请码交互无问题，该链路不再阻塞本期数据验证。
- 清理继续保留2100依赖的`api/results/provisioning/isop-2100-chain/`、`isop-2100-priority/`、`isop2092-first-deposit-20260928/`、`api/results/p0-controlled-flow-result.json`与`reports/database/20260929-fat/`；具体保留依赖见[整理记录](docs/project-cleanup-2026-10-05.md)。
- 旧异常会员／申请索引在忽略且0600的`api/local-state/requirement-records-fat.json`；2032复用会员定位在`api/local-state/isop2032-selected-member.json`。2027 API019／API020既有记录已产生待审草稿，不能当干净前置；只读字段复验与Codex权限恢复状态仍在`api/local-state/fat-readonly-fields-recheck.json`、`api/local-state/fat-readonly-fields-fixcheck.json`和`api/local-state/fat-codex-review-grant.json`。使用前只读查实时状态，不清理业务记录或重放异常申请；B保持用户指定Codex角色。
- 凭据、号码预留、Telegram队列／游标及workflow SQLite是运行状态，不按报告清理。旧任务`58bed509adb9b8a9`仍REVIEW未批准且配置hash已失效，不沿用旧确认或改hash绕过；恢复先读[Telegram续接](docs/telegram-next-session.md)。

## 有效授权与日常规则

- Jira提单、QA／开发负责人、群路由与已解决回归通知以[当前交付流程](docs/telegram-qa.md#bug-delivery)为权威。具体批次已有用户授权就沿用，不逐步重复确认；本批四单与群汇总已完成，不能由旧队列默认值推断下一批授权或目标群。
- 用户既有Telegram／Jira扫描及同范围脱敏AI分析授权保留；不扩大业务写入、BUG提交或发群范围。每个Story固定一名负责人，历史2027由Davinci负责；归档不自动恢复旧任务执行。
- 每轮fresh登录，不跨轮复用token；同账号API／UI串行接力避免互踢。P0、需求专项与资金链独立，完整资金链必须有真实UI投注；永久BASIC及资金号不用于KYC编辑试验。环境例外、部署版本未提供及素材限制见[环境手册](api/runbooks/ENVIRONMENTS.md)。
- 功能预期和API断言先由人工确认，AI在目标明确后加速执行，见[统一流程](docs/testing-workflow.md#人工确认预期与断言)。新需求API自动优先、UI人工验收；P0继续维护API与核心UI自动化，已有新需求UI实现保留兼容。
- 功能／流程变更同次更新日常说明及受影响入口，再记交接，见[维护入口](AGENTS.md)与[架构边界](docs/architecture.md)。保留npm／CLI和报告输出路径；凭据、证件、token及未脱敏资料不提交。

## 已实现与仍待落实

- 功能／API用例卡片、总表导出、统一API执行、UI人工包及回填已有实现；JSON是执行源，CSV供生成和审阅，登记状态不等于实测。日常分工见[用例流程](docs/testing-workflow.md)、[团队测试](docs/team-testing.md)及[命令范围](docs/commands.md)。
- TEST缺陷、QA／开发负责人、关联回读和短群汇总已通过定向操作验证；旧`qa:telegram -- submit`仍缺TEST／QA／目标群适配，不用于新批次或补发本批通知。超长附件及通用自动链路尚未完成验收。
- QA优先的已解决通知已保存，真实正文及送达有用户证据；提及实体、空QA、多QA及未知映射真实分支未验证，见[通知边界](docs/telegram-qa.md#resolved-notification)。不通过切换真实BUG状态测试通知。
- 用户首稿功能模板、JMeter／Postman导出选型与实现、测试空间位置及首份简体需求副本仍待落实；不能把讨论当作已上线功能。术语歧义与业务确认独立于简繁转换。跨团队Agent平台／权限／消息协议仍在[讨论阶段](docs/agent-collaboration-research.md)。

## 历史与本轮整理

- 其余32条需求从[历史索引](requirements/history/README.md)查询。原13条完成来源为09-18用户确认；10-05新增19条归档仅收敛范围，不新增完成／上线／PASS。2022主动复测暂停保留，归档或显式旧编号兼容不代表恢复执行；历史BUG提交仍须具体清单授权。
- 2092最新GGR决定（真实GGR减JP派彩、游戏类型各自独立计算）留在[历史问题与决定](requirements/history/archived-20261005/ISOP-2092/questions.md#q-04)，未按新规则回归，不自动移植为2100预期。后台模块规则与遗留覆盖从[模块入口](modules/README.md)读取。
- 独立班车评估项目已移至`/Users/rayleigh/jira-delivery-review`，相关后续工作在该项目继续。09-30工作流评估用户要求仅放本项目本地；误建Confluence页面427556927已核为trashed，勿再次发布，原评估Markdown整理前已缺失。
- 用户本轮再次授权删除无用重复历史测试记录。已退出静态原始证据和本轮去重范围统一记[整理记录](docs/project-cleanup-2026-10-05.md)，旧日期结论不冒充当前实测；不新建历史副本保留本页逐次计数或已替代下一步。
- 本轮另删除37个无用副本／缓存／重复历史文档，当前三个HTML及必要业务证据、账号和运行状态保持。文档、资产、语法与359项本地单测通过（首次沙箱回环限制已重跑解决）；链接／hash与实际边界只在[整理记录](docs/project-cleanup-2026-10-05.md#本轮验证)维护。没有业务API／UI、数据库写入、Jira修改或发群，未提交或推送。

- 10-05用户授权整理全部当前变更、合并代码并推送。提交范围为19条需求与6份日期记录归档、2100验收／补测／四单交付记录、状态默认当前／证据退出展示及日常入口整理；本地HTML、原始响应、凭据和运行状态继续忽略。提交前复核补齐Windows跨盘`--state`离线证据路径回退，HTTP路由与状态持久化保持；操作说明已同步。Git交付与本地校验结果见[提交整理](docs/project-cleanup-2026-10-05.md#提交与远端同步)。
