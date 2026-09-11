# 当前交接

更新：2026-09-11。已按用户授权清理全项目旧结果、扫描归档、临时脚本及重复视图，详见[整理记录](docs/project-cleanup-2026-09-11.md)。旧“全部历史文件保留”约定由此次清理指令替代。后续用户已授权合理合并远端并推送；本地累积修改先独立保存为ed0b5da，再整合origin/main的99c1d9c及之前4个新增提交。本次合并未执行FAT业务、数据库写入、BUG提交或发群。

## 当前入口

- 最新逐项开测（2026-09-11）：已按用户指令完成2031、2043新增统计、2028查询首轮；中文报告、失败解释及2032/2037编辑导出未执行原因集中在[本轮结果](requirements/api-test-round-20260911.md)。三个plan.json和API数据已落盘，2043旧查询保持兼容。2022继续等修复；通知消费、配置写入、导出任务均未执行，BUG提交仍需确认，测试过程不发群。下一步补本轮通知样本、导出订阅与文件完成契约，2037文档23列表头与需求24列需对齐。

- 提交准备及后续合并见[整理记录](docs/project-cleanup-2026-09-11.md#远端合并2026-09-11)。用户最新指令允许提交和推送，替代此前由用户自行提交的安排；合并保留双方有效内容、当前配置和证据。新对话先读取本文件和AGENTS.md，再按下面的续接顺序推进。

- 2027远端人工“通过”与Davinci负责人已逐行保留，新增C18“临近分行变更联动游戏类型限制”纳入18条业务总用例。来源、待关联的人工批次与自动化边界见[2027用例](requirements/ISOP-2027/test-cases.md)。冻结计划仍覆盖C01—C17，C18未实现独立自动断言；旧Restore失败、API候选、未回填manual.csv和当前原始结果均不因人工记录改变。

- ISOP-2022/2085已按用户最新“直接开测、逐轮出结果”指令完成FAT首轮与限定复核（2026-09-11），替代此前等全部条件齐备再执行的安排。新增统一plan.json、API数据视图及只读筛选/金额断言；现有53组合、48可执行，当前完整计划尚未全部按最新hash重跑。实际批次、计数、4项候选及空值契约差异集中在[问题评审](requirements/ISOP-2022/bug-review.md)。首轮和8项限定复核均保留真实失败，未算作整条业务/全量父需求验收；latest当前指向限定复核。每轮fresh登录，只读API与DB，没有造数/重算、BUG提交或发群。

- 待确认列表按requirements已有需求编号展示，子任务归并；终端和preview.md保持简洁，详细消息/用例缺口留在preview.json。本地`qa:telegram -- preview`不扫描或调用AI；`run --requirements ... --revision ...`按需求选择，多批次须用原--candidates明确选择。本轮未执行测试，验证与保留状态见[列表续接](docs/telegram-next-session.md#需求级待确认列表2026-09-11)。

- ISOP-2030当前仅有H5页面改版提测依据，原列表API来自扫描器默认范围，已纠正为手工UI。本地test_scopes限制同时用于预览与任务确认，8条总用例同步为人工UI；后续有明确API变更再评审。原候选、队列和证据未改，配置变更后使用新预览版本，详见[2030设计](requirements/ISOP-2030/design.md#测试分工与准备)。

- 扫描执行衔接：有plan.json的新任务使用统一API执行器，UI输出人工包；import-manual合并结果并产生新BUG评审版本。任务确认绑定计划hash与选择范围。--version记录声明版本，Telegram前后探针均匹配才核验。实现及本轮验证见[优化计划](docs/new-requirement-automation-plan.md#扫描执行与版本衔接2026-09-11)。本机配置默认写范围未扩大，活动任务及原证据保持。

- 最新范围澄清（2026-09-11）：**P0继续维护API与核心UI自动化；新需求API自动执行，UI人工执行，暂不建设新需求UI自动化。** 已有P0代码/用例/命令不变；旧新需求UI实现仅保留兼容，不列入后续待办。分工见[团队流程](docs/team-testing.md#自动化范围)。

- 常规需求文件分工见[目录约定](requirements/README.md#常规需求目录)：总用例与API数据分开，新结果/人工回填在reports/qa，实际候选产生后再整理BUG清单；不复制2027试点阶段记录或新增UI自动化目录。2022已实现API执行配置及本轮问题评审；已修正其契约评审中旧的UI自动化安排。现有文件及报告路径未迁移。

- 已按用户决定分离总用例与API数据：各需求cases.csv按业务场景汇总，api/data-cases.csv保存具体参数组合和断言，通过总用例编号关联。总表源为test-cases.md；自动执行源仍是plan.json或旧api/cases.json。`npm run qa:cases -- --all`离线更新，当前范围及验证见[测试流程](docs/testing-workflow.md#本次用例分离验证2026-09-11)。已有执行包、结果和业务状态未覆盖。

- [团队测试流程](docs/team-testing.md)：API自动执行优先，UI由AI整理用例、人执行并回填。当前执行包为`reports/qa/ISOP-2027/team-ready-20260911/`，人工表尚未执行；不要把准备视图当通过结果。
- [新需求计划](docs/new-requirement-automation-plan.md)：阶段1、2及固定UI能力已实施；不继续建设新需求UI自动化或通用混合流程，P0自动化继续维护。实施说明见[API阶段](docs/new-requirement-stage1-2.md)、[可选UI阶段](docs/new-requirement-stage3.md)。
- `requirements/ISOP-2027/plan.json`是唯一执行源。`npm run qa:requirement -- ISOP-2027`默认离线校验；默认自动侧排除人工项，显式`--only`、`--layer UI`或`--include-ui-automation`继续兼容已有UI能力。
- `reports/qa/ISOP-2027/latest.html`指向最近真实执行，不代表全量回归；当前为2026-09-11固定UI实测。旧API批次及历史归并结果已删除，不能再作为可导入证据。新结果默认只导出results.csv/results.html，额外视图用`--extra-views`。
- [需求入口](requirements/README.md)、[问题与决定](requirements/ISOP-2027/questions.md)、[准备清单](requirements/ISOP-2027/preparation.csv)保留业务规则和缺口；历史文字结论保持日期，原始文件已清理的地方明确注明。

## 下一步与未结事项

- 远端补充记录（提交ce0274a，2026-09-11）：Windows FAT无认证doctor网络检查通过，未登录或发送业务请求；2022业务仍受契约/样本缺口影响。原执行尝试和BLOCKED_DATA/BLOCKED_EXPECTATION记录已保留在[2022用例](requirements/ISOP-2022/test-cases.md)，不替代本机数据库准备核对或业务验收。

- 用户最新决定（2026-09-11）：2022等待修复，暂停主动复测；此前逐轮开测授权保留，但不覆盖本次暂停决定。已有问题与报告保持。收到修复/重新开测指令后再按明确范围fresh登录复验；BUG提交仍需确认，测试过程不发群。

- 团队实际执行当前manual.csv，回填六列并附脱敏证据；自动侧按本批范围执行，再明确选择真实来源导入。优先完善API数据与断言，UI按人工验收推进。
- [候选BUG](requirements/ISOP-2027/api/BUG-review-2026-09-10.md)尚未获建单批准。旧API证据已清理，提交前需按当前版本补充复现；Restore最近一次失败截图仍在当前UI批次。
- 异常测试会员未做业务清理。旧会员/申请定位信息收敛至忽略且0600的`api/local-state/requirement-records-fat.json`，只含标识和历史状态，使用前须只读查实时状态，不重放或核准旧异常申请。号码预留状态未改。
- B保持用户指定Codex角色，已执行的权限恢复结论见日期记录；普通角色新增复核权限契约、UI权限矩阵、状态1/4、精确原因最大长度、第三复核身份和故障恢复仍有缺口。分行名称与sid异常草稿不能用于补成功。
- [Telegram续接](docs/telegram-next-session.md)：任务`58bed509adb9b8a9`仍REVIEW且未批准，config_hash已与当前配置不同，不沿用旧确认或改hash绕过检查；原报告留作历史参考，后续BUG用当前批次补证据。本次整理未改队列或游标。Telegram新任务已能消费统一API结果和人工包回填；真实建单、关联后整批群清单及超长附件验收未完成。

## 当前有效约定

- 每个Story固定一名负责人；ISOP-2027由Davinci负责。父级优先查design明确子任务，执行前查Jira核对。ISOP-2027 FAT既有读写测试授权沿用，不重复确认；BUG提交仍需确认具体清单。
- 测试过程、报告和候选留本机。具体PRODUCT BUG获确认后，整批建单并关联Story成功，再一次性发测试群清单；部分失败或无PRODUCT BUG不发。
- P0、需求专项和资金链独立。完整资金链必须有真实UI投注；API清流不能充当投注证据。每轮fresh登录，不跨轮复用token。
- 数据库只读；写入绑定本轮专用账号和记录。业务失败不靠后续成功接口改判。永久BASIC账号和资金号不用于KYC编辑试验。
- FAT/UAT例外以[环境手册](api/runbooks/ENVIRONMENTS.md)为准。部署版本未提供不阻塞既有FAT授权；合成PNG上限512000字节。Jira BUG状态推送已由用户确认，不重测该脚本。
- 保持npm/CLI入口、P0路径兼容；`.env.ui-p0.fat`仍供旧UI资金入口使用。凭据、SQLite及号码预留是运行状态，不按报告清理。后续清理先核对活动任务和引用，不自动套用本次删除范围。

## 验证入口

提交前核对及后续远端合并见[整理记录](docs/project-cleanup-2026-09-11.md)；此前扫描执行与版本衔接的阶段验证见[优化计划](docs/new-requirement-automation-plan.md#扫描执行与版本衔接2026-09-11)。Git提交/推送按用户最新授权处理，本次未运行真实API/UI业务测试、创建BUG或发群。

最新整理验证只在[整理记录](docs/project-cleanup-2026-09-11.md)维护。本地`npm run check`不连接FAT/UAT，也不证明业务或Windows/Linux、CI验收通过。架构与命令分别见[架构说明](docs/architecture.md)、[命令说明](docs/commands.md)。

2022本轮代码校验：`npm run check`通过（298项单测）；首次沙箱因本地测试端口监听受限失败，离线校验网络权限重试后通过。计划离线导出通过。业务结果以问题评审链接的两个批次为准，不由本地校验替代。

2022报告中文展示（2026-09-11）：按用户要求，首轮与限定复核的原results.html/results.csv已更新为中文场景和实际结果说明；HTML状态显示通过/失败/未执行/执行出错，编号及原技术断言放在展开详情。原result.json和冻结快照hash保持，原视图备份为results.before-chinese.*；没有重跑业务或改判。公共展示转换在qa_core/result_language.py，2022历史标题适配在filbet/record_report.py，统一执行与离线重建入口后续沿用。`npm run check`通过（300项单测），浏览器实查中文布局及14项失败筛选通过。

接口最新扫描（2026-09-11）：backend_api本地与远端main均b8daa7d，较ca3c1c2新增2提交、5份合规报表文档变更；主要为2028的总GGR、JP贡献/派奖字段，关联按内容推断。详见[2028接口评审](requirements/ISOP-2028/api/contract-review.md)。inventory/catalog已离线刷新，累计资产变化与本次提交增量分开记录；P0范围不变。2022两处查询文档无改动，此次没有业务测试、Telegram扫描或发群。

2022报告时区（2026-09-11）：按用户要求，20260911T092623Z-a2618c63/results.html的报告时间改为2026-09-11 17:26:23（UTC+8）。公共case_report渲染器后续将带时区的报告时间及执行时间转为东八区；未注明时区的值保留原文。原始JSON、批次编号和测试结论未改，没有重跑业务。跨日和已有+08:00转换校验通过；`npm run check`通过（300项单测，首次沙箱端口限制后提权重试）。

2022—2072未测接口盘点（2026-09-11）：已按现有13个需求核对提交与执行证据，见[范围清单](requirements/api-coverage-review-20260911.md)。重点遗漏为2031余额通知/已读、2043五处新增JP统计、2028五处报表/导出；2032编辑/导出与2037导出亦未测。历史查询已测与原结果已清理分开记录，2022继续等待修复。本轮仅盘点，没有业务测试、BUG提交或发群。

逐项开测代码验证（2026-09-11）：`npm run check`通过（303项单测，localhost限制后重试）；计划离线导出及中文报告证据链接核对通过。实测计数只在[本轮结果](requirements/api-test-round-20260911.md)维护。
