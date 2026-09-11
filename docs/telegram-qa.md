# Telegram 提测与测试群评审

用户于2026-09-10最新确认：每个Story固定一名测试负责人，所有子任务和后续批次沿用；测试前确认保留。测试过程、报告和候选BUG仅保存在本机，具体BUG确认后先批量创建Jira Bug并关联Story，整批完成后才向测试群发送一份BUG链接清单。此前群内认领、过程通知和报告分片方案作废。原代码更新通知工作流保持原用途。

当前实现包含持久队列、统一API执行适配、UI人工清单与回填导入、AI缺陷分类、本地报告、版本化确认及Jira逐项提交。2026-09-11起，新的提测任务不启动专项UI浏览器；P0的API与核心UI自动化保持。接入参数与真实环境验收仍须完成，代码存在不代表服务已上线。最新机器接入状态以 [交接](../AI-HANDOFF.md) 为准。

## 首次接入需要补充的信息

本地凭据默认读取根目录 `.env.telegram`，包含 `TELEGRAM_BOT_TOKEN`、`JIRA_EMAIL`、`JIRA_API_TOKEN`；也可指定 `--credentials <本地文件>`。`requirements/.env.telegram` 不再是默认入口。身份与群路由保存在忽略的 `config/telegram/local.json`，模板见 [配置模板](../config/telegram/example.json)。

- 只登记Davinci、ukrwlof、Rayleigh三位测试的数字ID，用于Story唯一负责人配置和BUG确认。所有群成员都可提测，不设提测人白名单。原消息@的人不自动成为负责人。在`stories.<Story>.tester_id`绑定唯一负责人；未配置可扫描，但禁止确认执行。不同运行和子任务不能另行认领。ISOP-2027用户已指定Davinci。
- 三人在测试群发 `/whoami@FilbetQABot`，本机运行 `npm run qa:telegram -- identify` 读取数字ID后填入本地映射。此命令只查看前100条可用更新，不推进游标、不发消息、不测试。
- 首轮试跑ISOP-2027、FAT，沿用现有FAT后台测试账号，本地 `account_email` 与实际环境配置保持一致。环境文件中的 `ADMIN_EMAIL` 必须匹配，密码和登录验证也必须属于该账号；Jira账号不是业务后台账号，不用Jira邮箱限制后台登录。
- UI人工步骤在需求plan.json的delivery字段维护。旧[UI配置模板](../config/telegram/ui.example.json)只供既有独立工具兼容，不再由扫描后的run自动执行。未实现人工交付的需求明确记NOT_RUN。
- 版本指本次部署的发布标识，例如构建号或Git提交号。当前项目没有提供时记“未提供”，不阻塞测试；不因此声称已核实部署版本。配置了版本探针且有明确版本时，前后核对不一致会阻塞。

普通“工单 + @测试 + 提测/提測”消息需要机器人能接收群内普通消息。在BotFather执行 `/setprivacy`，选择机器人并Disable，然后移出并重新加入提测群使设置生效；见 [Telegram隐私模式](https://core.telegram.org/bots/features#privacy-mode)。扫描前检查此项，不将不可见误判为无人提测。

本机需要Node、Python及已认证Codex CLI；Playwright浏览器继续供P0使用。新需求API由确定性执行器运行，页面场景由人工执行；AI只分析本轮脱敏材料。原型规则先整理到需求文档，不能只从当前页面反推验收预期。

若扫描提示`Codex CLI not found`，在能运行Codex的终端执行`command -v codex`，把输出的实际可执行文件绝对路径填入本地配置的`codex_executable`，并用该路径执行`--version`验证。VS Code扩展目录带版本号，升级后旧路径可能失效；不要填写扩展目录或项目目录。`qa:telegram -- check`只检查配置结构，不能代替可执行文件验证。修复后重新运行扫描即可重试本机已保存的待分析消息，无需重发。配置变更后使用重新扫描生成的预览版本确认任务。

## 手动扫描一次

```bash
npm run qa:telegram
```

该命令读取并持久保存脱敏的提测群消息，由Codex CLI分析自然语言与上下文（含链接、回复），整理提测/部署通知与相关说明，撤回或歧义仅作信息备注，优先从requirements/*/design.md的明确“子任务：”记录查父Story，缺失或冲突时只读查询Jira。终端和`reports/telegram/preview.md`只展示需求级待确认列表：需求编号、名称、环境、配置范围及提测判断；不展开原始消息、逐条AI解释或用例阻塞原因。不测试、不发群消息、不创建BUG。

待确认列表仅包含已归属到`requirements/ISOP-*/`现有目录的需求，例如ISOP-2085归到ISOP-2022。同一需求一行，同一环境/版本/范围的子任务合并；不同批次保留独立选择，不能一次隐式全选。目录存在但没有待确认提测记录的需求不列入，目录外或归属未核实的工单保留在详细JSON的unmatched中，不删除消息。`preview.json`继续保存来源工单、版本、引用消息、AI依据、负责人和全部执行缺口。未知环境按配置默认值显示并明确标待核实；仅请求部署或歧义消息不标成已明确提测。配置范围是执行配置，不能据此扩大消息提测范围或认定完整测试已就绪。

扫描器的历史scopes默认api/ui，不代表检测到了API修改。已评审需求可用本地`stories.<需求>.test_scopes`限定测试层级，取候选范围与该配置的交集，不自动扩大；无交集则必须核实，不能确认执行。2026-09-11核对ISOP-2030仅有H5提测和页面改版依据，配置为`["ui"]`，列表与确认任务均只含手工UI。旧候选原记录不改，preview保留intake_scopes和限定依据；后续明确出现API变更时重新评审配置。未配置此字段的需求保持原范围，不据默认api/ui声称接口已经修改。

只查看已保存的清单可运行`npm run qa:telegram -- preview`：只读本机队列并刷新preview.json/preview.md，不获取新消息、不调用AI、不改队列或扫描游标。输出标明来源扫描时间；不能用于发现新提测。AI分析未完成时保留候选供查看，不提示执行run。

每批最多处理100条未分析消息，只有消息本身正文、caption或链接含ISOP工单号才交AI；可带最近50条同样含ISOP的历史消息。不再带入普通邻近聊天，也不因“我在测试、不用理”生成候选。没有ISOP消息则跳过AI，剩余消息下次扫描继续处理。分析失败保留消息，下次即使Telegram更新已过期也可本地重试；旧版已经消费但未保存的消息无法恢复。AI必须覆盖每条新消息，工单必须出现在引用证据中；未分析完不能执行；AI的歧义或撤回标签仅作备注，不隐藏或取消候选。是否测试完全由用户选定；工单所属Story和允许环境仍须核实。当前仅处理新message更新，编辑旧消息请另发补充消息。

同一批证据重试复用内容摘要命名的目录，覆盖本批日志/输出而不新增随机目录。AI上下文与结果保存在忽略目录 `reports/telegram/intake/`，待处理状态在SQLite中；身份以本地匿名标识提供。AI质量仍需首轮真实消息确认，离线模拟不能证明业务理解准确。

默认按上次已保存的Telegram游标增量接收，记录上次扫描时间、本次起止时间及前后游标；时间记录不代替游标，不因消息延迟抵达而丢弃。首次升级沿用已有游标，旧扫描时间未知则明确显示首次记录。每天更新 `reports/telegram/scans/YYYY-MM-DD.json` 一份汇总（扫描次数、收到更新总数、最新结果），不为重复空扫描无限追加文件。

可选择起始时间，必须带时区：

```bash
npm run qa:telegram -- --since 2026-09-10T15:00:00+08:00
```

此选项筛选机器人仍能提供及本机保存的未分析消息；时间前的消息保留为排除状态，之后选择更早时间可以纳入。已分析消息不因重复选择而重新调用AI或生成任务，已生成候选仍显示供核对；无时间戳消息保留待分析。默认不自动恢复此前明确排除的消息。没有任意群历史补抓能力。超过时间窗口的相关历史可以作为上下文，不作为新的提测触发。

确认列表与测试范围后执行终端给出的命令：

```bash
npm run qa:telegram -- run --requirements <需求编号,需求编号> --revision <预览版本>
```

例如选择`ISOP-2022,ISOP-2032`，只解析为当前预览中这些需求的明确批次。若同一需求有多个环境、版本或范围，命令拒绝隐式合并，查看preview.json后用兼容入口`run --candidates <候选ID,候选ID> --revision <预览版本>`选择；两种选择参数互斥。目录外工单不能通过旧候选ID绕过需求列表。原有负责人、试点范围、环境及计划hash检查继续生效，列入待确认不代表已经具备完整测试条件。

清单按父Story、环境、版本和执行范围归并，保留子任务issues、成员member_ids及原消息source_messages。同一需求只执行一次；不同环境或范围不混合。确认绑定合并清单与配置，选中后全部成员标为已确认；变更后需重新预览。执行前逐个子任务只读核实Jira父Story，若与本地记录不一致则停止，更新文档后重新确认。当前试点只开放ISOP-2027；执行所选Story已配置专项，不把子任务提测解释成整Story已验收。报告、候选BUG和过程事件仅留本机；不在测试群通知。

有plan.json的需求在任务预览中增加执行计划摘要、可执行API/人工用例数量、未就绪原因及允许写范围。确认绑定计划文件hash和选择范围；确认后修改计划会停止执行，需重新预览。尚未迁移的需求继续使用旧查询入口，UI不会回退为自动浏览器执行。

UI清单位于`reports/telegram/runs/<job>/team-packet/manual.csv`；按[团队回填规则](team-testing.md#人工怎么回填)填写后导入：

```bash
npm run qa:telegram -- import-manual --job <job> --revision <当前报告版本> --manual reports/telegram/runs/<job>/team-packet/manual.csv
```

此命令只读本批冻结配置和明确API证据，复用人工导入校验，并调用AI重新整理API与人工UI的候选BUG。不登录业务、不重跑测试、不创建Jira或发送消息。API失败及中断状态保留；原报告和每次导入证据留存，新报告产生新revision，原确认不再适用。只接受尚未批准的REVIEW任务；已批准/提交任务不可回填覆盖。旧活动任务没有团队包时不能直接导入新清单。若AI分类失败，结果保留，使用revise补充评审。

核对本机`reports/telegram/runs/<run-id>/report.md`里的具体PRODUCT BUG及当前列表revision后，显式确认并提交：

```bash
npm run qa:telegram -- approve --job <run-id> --revision <候选列表版本> --bugs B1,B2
npm run qa:telegram -- submit
```

`approve`是本机操作者对固定Story负责人所审阅列表的明确确认，绑定当前配置、报告版本和具体PRODUCT编号，本身不写Jira、不发消息。保留测试群`/approve@YourQABot <run-id> <revision> B1,B2`作为兼容输入，仅固定Story负责人可确认；不再需要群内先收到报告。`/claim`不再分配负责人；`/whoami`和`/status`不触发群回复，身份通过`identify`在终端查看。

`submit`逐项创建真正Bug并关联Story，全部成功后只发送一份含编号、标题和Jira链接的清单。短清单为一条消息；超过单条长度则一次发送完整文本附件，不拆成逐行通知。任何一项创建或关联失败，整份清单暂停发送；本机保留已创建编号和不确定状态，恢复时不重复建单。未确认项不提交，环境/数据/脚本/契约问题不自动建产品BUG。没有PRODUCT BUG时不造测试BUG、不发“无BUG”消息。`submit`同时保存新提测为候选，但不会启动其测试；没有常驻监听。

Telegram Bot API不提供任意群历史搜索，待处理更新最多保留24小时，超期或机器人原本不可见的消息需要重发。默认最多20页、每页100条、timeout=0；可用 `--max-pages` 指定1—100页。游标与候选持久化，重复更新不重复入队。已有Webhook时拒绝扫描，不擅自删除。

```bash
npm run qa:telegram -- check
npm run qa:telegram -- verify
npm run qa:telegram -- status
```

`check`离线检查字段；`verify`只读验证机器人身份、群可达性/隐私权限、Webhook、Jira登录及试点Story，不读取提测更新或写入外部系统。若Python缺少系统CA，可在本机凭据文件配置 `QA_CA_BUNDLE` 指向可信证书包，保持TLS验证开启。旧poll/worker/service-files入口和未加载的launchd配置已撤下。

## 测试与证据边界

有plan.json时调用`run-requirement.py`，只执行任务确认的automatic API/后台FLOW；通过本次专用结果索引读取真实报告，不搜索latest补数。执行器再次核对计划hash，导入时核对Story、环境、版本、用例集合、步骤及退出码。原始API结果仍在`reports/qa/<Story>/<run-id>/`，机器人目录保存来源与摘要。无plan.json时保留旧`run-requirement-api.py`查询入口及其结果路径。

Story可选`execution`配置：

```json
{
  "execution": {
    "case_ids": ["review-list-state-1", "2027-UI-001"],
    "allow_write": [],
    "insecure": false
  }
}
```

上述示例放入`stories.ISOP-2027`。case_ids使用展开后的执行编号，省略表示按本批api/ui范围选择；API范围对应automatic，UI范围对应manual。allow_write默认空，需写入但未开放的用例记NOT_RUN，不会为准备UI样本自动扩大写范围。已获授权的2027 FAT完整API流程可由维护者将kyc-review、kyc-permissions写入此列表，再按新预览确认执行；测试授权沿用，配置本身不替代任务范围确认。insecure仅在既有测试环境证书例外下启用。配置变更使旧任务配置hash失效，本次未改本机配置或活动队列。

统一执行器当前仍限定FAT，未扩展UAT业务授权。单独运行可用`--version <发布标识>`记录声明版本，缺省“未提供”。声明版本会传入执行包、原始API结果和HTML；它不等于核验。Telegram运行前后均有匹配的版本探针才在任务报告标verified，原始API结果保留declared；不修改原始结果制造核验。人工回填只声明其清单版本，不将API前后探针当成人工操作时的核验。部署变化时阻塞状态在后续导入中继续保留。

UI步骤及预期来自冻结plan.delivery；总用例维护源仍为test-cases.md。人工未回填保持NOT_RUN，已有UI自动化PASS不作为人工结果。数据库保持只读，业务失败不自动重跑。

进程有超时与后代清理，业务失败不自动重跑；重启时执行中的任务转 INTERRUPTED，避免不确定状态下重放。运行前后部署检查不一致时本轮 BLOCKED。AI分析失败时保留实际结果并标明需人工整理，空 BUG 列表不意味着无缺陷。

每轮产物位于忽略目录 `reports/telegram/runs/<run-id>/`：`run.json`、需求快照、workflow来源清单、API证据摘要、team-packet、人工导入证据、`report.json`与`report.md`。BUG候选统一在report.md确认，避免同时维护另一份可提交清单；需求bug-review.md如需保留，只记录复现说明和本批评审入口。候选 BUG 只允许引用本轮失败用例的证据文件。群里发送脱敏文本，Jira描述带 run-id 与本机证据目录；尚未托管截图或提供外网报告链接。

## 修订、提交与恢复

测试负责人可先核对本地报告；维护者通过下列命令导入修订后的 `{summary, bugs}`，保留原执行结果，同步本地JSON/Markdown报告并产生新版本，不发送测试群。该动作本身不批准 Jira 写入。

```bash
npm run qa:telegram -- revise --job <run-id> --review-file <本地JSON文件>
```

单次批处理使用本机 Jira REST 凭据，不继承当前 Codex 对话里的连接器会话。2026-09-10只读核对 ISOP：Bug 类型 ID 为10676，层级0，与 Story 同级；本机采用项目已存在的 `Relates` 链接关联 Story，保留真正的 BUG 类型。该模式不会把 Bug 伪装成子任务，也不修改项目层级。Jira报告人默认使用服务凭据身份；团队邮箱映射不等于已获得修改报告人的权限。

创建前查询稳定缺陷标签去重。确认后的批次逐项创建并保存 Jira key，再关联 Story；创建请求发出前先持久化 INTENT。超时、断线、关联失败或进程中断时停止，不盲目重建。

```bash
npm run qa:telegram -- reconcile-jira --job <run-id>
npm run qa:telegram -- retry-jira --job <run-id>
```

`reconcile-jira` 只读查询不确定的创建结果；找到后记录 Jira key，找不到保持不确定，不把暂时搜索不到解释为未创建。`retry-jira` 只恢复已有明确人工确认、配置未改变、没有未决 INTENT 的任务；已创建项仅补关联，不重新创建。配置变更会阻止旧确认继续提交，需要重新核对。

队列/outbox仅允许`bug_summary`且对应批次为SUBMITTED时投递。历史未发过程/报告消息标为抑制（sent=2），保留记录但不补发。完成清单持久化保证消息失败可继续发送；Telegram `sendMessage` 没有应用层幂等键，发送成功但本机尚未来得及标记时，恢复可能重复一条通知。业务测试与 Jira创建不会因此重复。请保留 SQLite 和同轮证据，不删除状态库作为“重试”。

## 验证

`npm run check` 包含离线队列/确认/Jira故障模拟、输入与AI证据校验、进程超时，以及本机回环 HTTPS 的真实 Playwright 测试。浏览器夹具不访问业务系统；没有 Node/OpenSSL 或已安装浏览器时按测试说明跳过。沙箱可能需要允许回环监听。真实Telegram群权限、Codex账号、FAT/UAT登录/页面和Jira写入仍须分别验收。

实现依据：[Telegram Bot API](https://core.telegram.org/bots/api)、[Codex非交互模式](https://developers.openai.com/codex/noninteractive)、[Jira创建问题](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/)、[Jira关联问题](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-links/)。
