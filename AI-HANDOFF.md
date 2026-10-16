# 当前交接

更新：2026-10-16。用户决定除输值返利外其他需求全部归档，清理无用历史测试资料，常用逻辑留在项目，低频事项按Jira及原文回查。当前仅 **ISOP-2090**；其余10个当前目录已移入[本批归档](requirements/history/archived-20261016/README.md)。归档不表示完成、上线、已修复或PASS，也不恢复旧测试、开户、资金或通知任务。

## 当前需求与下一步

- [2090设计](requirements/ISOP-2090/design.md)、[问题与决定](requirements/ISOP-2090/questions.md)、[测试重点](requirements/ISOP-2090/test-cases.md)是当前入口。已合入远端`f05ed49`的10-12正式测试资产；Jira／Confluence来源读取截至2026-10-12，视觉来源仍为10-06，v2.0依据评论17491（09-28）。合并本身未刷新远端或重做业务。
- 已确认统一门槛／上限、唯一规则归属、净输计算、仅已结算有效注单、GMT+8隔日05:00派发，以及封顶前报表和实派账变的区别。不重开已定规则，不套用首页BI或代理GGR公式。
- 仍需确认Q-01 JP字段映射、Q-02日内版本／跨日／更正重跑、Q-03停用指定组及推荐语义。取得答复后写回本单规则及测试预期；冻结配置下的已明确场景可继续准备，不必等待全部问题解决。
- 已有23张正式功能卡、CSV、日报／客户端只读及受控配置CLI与共享模块，已登记PARTIAL证据基线；尚无完整`plan.json`／`api/cases.json`或统一P0集成。10-12定向测试及四项候选分别见[实测记录](requirements/ISOP-2090/verification-20261012.md)、[缺陷评审](requirements/ISOP-2090/bug-review.md)，失败与未测继续保留。
- 10-12没有日结命令，当时计划10-13对账；仓库尚无该后续完成证据，不将过期安排当已执行。续接先核实际数据／配置快照、05:00前证据及版本，顺序见[执行安排](requirements/ISOP-2090/execution-order.md)。本轮只做Git整合和W27需求扫描，不触发业务测试。

## 常用能力与日常入口

| 用途 | 维护入口与边界 |
| --- | --- |
| 资金闭环、KYC、权限及只读统计检查 | [业务规则与已有实现](skills/business-rules.md)；已有模块继续复用，定向场景不冒充通用覆盖 |
| 首页BI统计口径 | [模块说明](modules/admin/home-bi/README.md)及[问题状态](modules/admin/home-bi/questions.md)；保留决定日期，2190分类分母已定、除零仍待确认 |
| 代理多端及身份／归属核对 | [代理模块](modules/agency/README.md)、[后台手册](api/runbooks/ADMIN.md)；精确UID对齐源记录与筛选，尚无完整通用对账入口 |
| 用例、API执行、人工回填、Xmind | [测试流程](docs/testing-workflow.md)、[团队交付](docs/team-testing.md)、[Xmind说明](docs/xmind-test-cases.md)；状态登记不等于实测 |
| Jira与群交付 | [当前交付流程](docs/telegram-qa.md#bug-delivery)；已验证定向操作与尚未适配的旧通用入口分开处理 |

保留规则见[架构说明](docs/architecture.md#常用能力与资料保留)：已有共享实现优先复用；常用方法和业务口径进入日常文档；低频厂商／临时数据准备保留Jira定位，不另建框架或恢复旧专项脚本为门禁。功能／流程变更须同步日常入口，不能只记交接。

## 归档事实与恢复边界

- 2100及代理记录保留历史判断。10-05早批失败、晚批部分恢复及未取得主管理真实CSV分别看[验收范围](requirements/history/archived-20261016/ISOP-2100/acceptance-20261005.md)和[回归记录](modules/agency/regression-20261005.md)，不判全量通过。独立代理管理首页排除，代理自己首页仍核；佣金停算停发是用户要求，后台实际停止未独立验证。
- 10-09后续已记录三名会员身份归属拆行、末页可达性及代理NGR明细／小计／总计的定向恢复；同窗口JP对账仍有源差异／截止点边界，见[10-09修复与JP记录](modules/agency/pagination-20261009.md#10月修复复验)。这比10-07记录更新，但不代表全源或整体统计通过。
- 用户原有10-07修改已保留：[会员日统计空身份核查](modules/agency/verification-20261007-member-identity.md)与[2100来源同步](requirements/history/archived-20261016/ISOP-2100/evidence-sync.md)。当时三名会员主档有身份，月报同UID空／正常身份拆行且组合筛选漏金额；Console对象有空字段，原始传输body、封装、源SQL／DB及部署未核，不能认定正常脱敏或已修复。
- 10-09选既有AG01–AG05各3直属（复用5名、增加10名）的KYC及资金准备已完成记录见[数据准备](modules/agency/preparation-20261009.md)，不得重放注册、KYC或充值。10-05创建15个新代理及各1个直属已有日期记录；成功开户／开通不可重放。域名三条件复现未完成，归档后不继续临时启用、注册或提交。具体历史范围按[代理日期记录](modules/agency/verification-20261005.md)回查。
- A_kyc、M1／M2／M0及旧异常申请不是干净前置；M0保持零活动。M2曾业务false但实际落单扣款，原创建FAIL不改，不重放提现或调用成功接口制造通过。数据库始终只读；恢复任何业务前先查实际后态。
- 10-05四单与提测发布群汇总已完成，用户确认送达但本地消息ID缺失，不补造、不重发。旧`qa:telegram -- submit`仍缺TEST／QA／目标群适配，不能据旧队列默认值推断当前授权；旧任务`58bed509adb9b8a9`为未批准REVIEW且配置hash失效，恢复先读[Telegram续接](docs/telegram-next-session.md)。
- 凭据、账号定位、号码预留、执行游标、SQLite及消息去重／确认状态属于运行状态。本次未清理；当前工作区并不具备旧文档列出的全部本机资料，缺失时须先恢复或只读定位，不能假定文件仍在。

## 证据与本轮验证

本轮删除的重复旧快照、缓存，与整理前已缺失的报告／附件分开登记在[10-16整理记录](docs/project-cleanup-2026-10-16.md)。日期摘要仅说明当时记录；原始证据不可用时不得充作可直接复验的附件。保留10-07最小摘要，未删除仍被执行器和离线校验使用的计划、CSV及接口配置。

状态页保持39项历史信息，默认仅显示当前2090；归档不清空人工修订、自动记录或历史事件。当前本机workflow SQLite缺失，状态页此次维护沿用既有离线快照，不以空数据库重建历史。npm／CLI和报告输出路径保持兼容。实际离线校验及未验证边界统一记整理记录，本次没有业务API／UI、数据库、Jira或群消息操作。

## 其他保留约束

- 远端10-09的[Time工具及Mac分享包](tools/time/README.md)已合入，命令入口保留；历史439项全量通过属于10-12那台运行环境，不覆盖本机Python版本／浏览器缺口。10-12后台动态TOTP与暂缓攻击调查的决定沿[后台规范](api/runbooks/ADMIN.md#后台登录规范)，成功登录不证明异常根因。

- 每轮fresh登录，同账号API／UI串行；P0、需求专项与资金链独立，完整资金链必须有真实UI投注，永久BASIC及资金号不用作KYC编辑试验。人工确认功能预期与API断言，环境边界见[环境手册](api/runbooks/ENVIRONMENTS.md)。
- 用户首稿功能模板、JMeter／Postman导出、测试空间与首份简体副本仍未落实；跨团队Agent平台仍在[讨论阶段](docs/agent-collaboration-research.md)，不当已上线能力。
- 班车评估后续在`/Users/rayleigh/jira-delivery-review`。09-30工作流评估仅放本地，误建Confluence页面427556927已核为trashed，勿再发布；原评估Markdown此前已缺失。本次用户已明确授权合并当前代码、概述提交并推送，完成后扫描看板322的2026W27；当前Git整合保留远端10-12能力与本机10-16归档。
