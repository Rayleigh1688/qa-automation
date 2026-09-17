# 需求历史评审与测试记录（2026-09-07—2026-09-11）

2026-09-15按用户授权集中整理。本文保留原日期的评审、失败依据和执行边界，原位置的6份零散Markdown已移除；相对链接已调整。正文中的“当前/本轮/未测”仅指所属历史日期，不作为当前状态。

当前入口：[需求索引](../../requirements/README.md) · [2026-09-14班车报告](../../requirements/test-round-20260914-seven.md)。原始测试JSON、冻结计划和报告未在本次清理中删除；2026-09-10原始结果已在此前清理退出，以下文字不恢复其可复核性。

## 原记录索引

| 原位置 | 合并位置 | 原Markdown SHA-256（合并前） |
| --- | --- | --- |
| `requirements/review-summary.md` | [历史章节](#review-20260907) | `6ec36562693b9b55a831c6d1063d7dd03e54e01bd28a67758a2aa001bc70f633` |
| `requirements/api-coverage-review-20260911.md` | [历史章节](#coverage-20260911) | `79150fd43d0d5ef06f81852f31ff36a049b0c64f329cbdfa89f73457a5060092` |
| `requirements/api-test-round-20260911.md` | [历史章节](#test-20260911) | `65f47edd1880e7eb6a5a489644b33318062ae069eb64ba4e9d2650445f25d860` |
| `requirements/ISOP-2032/api/execution-2026-09-10.md` | [历史章节](#isop-2032-20260910) | `9ebb4272c38f2f1f3d6244f24bacf0b4b958a10a795b6c6a1e87beaf84b96a28` |
| `requirements/ISOP-2037/api/execution-2026-09-10.md` | [历史章节](#isop-2037-20260910) | `cb4ce196ea7026aecd0a7c0184f7b71d447df8e246c7d04a7dae09d6fc493cab` |
| `requirements/ISOP-2043/api/execution-2026-09-10.md` | [历史章节](#isop-2043-20260910) | `b4ccafb2071881f6ad7b69f57760e24af5c6b68c5ee96d6c61b05696fc8d8b15` |

<a id="review-20260907"></a>

## ISOP-2022 之后的新 Story：评审与分派

首轮评审快照：2026-09-07（UTC+8）；ISOP-2031/2032于2026-09-08复审，更新见下。本批为需求梳理和测试设计，不是业务验收报告。逐条可分派用例见 [需求索引](../../requirements/README.md)，当前执行状态只维护在各自用例文件。

<a id="review-20260907-查询范围与完整性"></a>

### 查询范围与完整性

已能访问用户提供的 [Jira项目列表](https://alibaba-international.atlassian.net/jira/software/projects/ISOP/list?jql=project%20%3D%20ISOP%20ORDER%20BY%20created%20DESC%2C%20cf%5B10019%5D%20ASC)。使用Jira连接器按Story类型和创建时间查询，避免把后建的子任务当成新需求，也不只按编号大小筛选。

```jql
project = ISOP AND issuetype = Story
AND created >= "2026-09-02 22:17"
ORDER BY created DESC, key DESC
```

边界Story ISOP-2022实际创建于`2026-09-02T22:17:31.609+0800`；按完整创建时间排除基准及更早项。返回一页且isLast=true，无后续页；剔除基准后共11个Story，最新为ISOP-2070。覆盖的是本次读取快照，不包含之后新建或更新的需求。11个Story关联的23个子任务也已读取，正文为空、未见评论补充。

<a id="review-20260907-创建时间倒序清单"></a>

### 创建时间倒序清单

| 创建时间（UTC+8） | Story | 首轮审阅范围 | 分派入口 |
| --- | --- | --- | --- |
| 2026-09-07 16:47:15 | [ISOP-2070](https://alibaba-international.atlassian.net/browse/ISOP-2070) Funky 時間回傳問題 | Funky纯日期、+8日界、重试 | [设计](../../requirements/ISOP-2070/design.md) · [问题](../../requirements/ISOP-2070/questions.md) · [用例](../../requirements/ISOP-2070/test-cases.md) |
| 2026-09-07 00:20:36 | [ISOP-2043](https://alibaba-international.atlassian.net/browse/ISOP-2043) 管理後台 - 新增 JP 資訊 | 会员/游戏/财务五组JP表单 | [设计](../../requirements/ISOP-2043/design.md) · [问题](../../requirements/ISOP-2043/questions.md) · [用例](../../requirements/ISOP-2043/test-cases.md) |
| 2026-09-07 00:06:12 | [ISOP-2041](https://alibaba-international.atlassian.net/browse/ISOP-2041) JP 注單寫入方式調整 | JP字段拆分、历史修复、资金不变 | [设计](../../requirements/ISOP-2041/design.md) · [问题](../../requirements/ISOP-2041/questions.md) · [用例](../../requirements/ISOP-2041/test-cases.md) |
| 2026-09-05 00:32:02 | [ISOP-2038](https://alibaba-international.atlassian.net/browse/ISOP-2038) 合規後台 - 移除 Jackpot 記錄選單 | 菜单和旧路由移除 | [设计](../../requirements/ISOP-2038/design.md) · [问题](../../requirements/ISOP-2038/questions.md) · [用例](../../requirements/ISOP-2038/test-cases.md) |
| 2026-09-05 00:16:03 | [ISOP-2037](https://alibaba-international.atlassian.net/browse/ISOP-2037) 合規後台 - 全平台投注紀錄增加欄位 | 四JP列、Multi、类型筛选、24列CSV | [设计](../../requirements/ISOP-2037/design.md) · [问题](../../requirements/ISOP-2037/questions.md) · [用例](../../requirements/ISOP-2037/test-cases.md) |
| 2026-09-03 18:39:25 | [ISOP-2032](https://alibaba-international.atlassian.net/browse/ISOP-2032) 用戶端 - 投注返利活動 | 活动配置、返利计算、派发/流水、通知、报表 | [设计](../../requirements/ISOP-2032/design.md) · [问题](../../requirements/ISOP-2032/questions.md) · [用例](../../requirements/ISOP-2032/test-cases.md) |
| 2026-09-03 18:38:52 | [ISOP-2031](https://alibaba-international.atlassian.net/browse/ISOP-2031) 用戶端 - 新增金額動畫效果 | 事件范围、通知去重/到期、金额动画 | [设计](../../requirements/ISOP-2031/design.md) · [问题](../../requirements/ISOP-2031/questions.md) · [用例](../../requirements/ISOP-2031/test-cases.md) |
| 2026-09-03 18:37:08 | [ISOP-2030](https://alibaba-international.atlassian.net/browse/ISOP-2030) 用戶端 - 遊戲頁面改版 | Header、Games、Rewards、Filcoin、My | [设计](../../requirements/ISOP-2030/design.md) · [问题](../../requirements/ISOP-2030/questions.md) · [用例](../../requirements/ISOP-2030/test-cases.md) |
| 2026-09-03 18:36:44 | [ISOP-2029](https://alibaba-international.atlassian.net/browse/ISOP-2029) 用戶端 - 免費旋轉領取文案調整 | 领取成功文案、两按钮、既有流程回归 | [设计](../../requirements/ISOP-2029/design.md) · [问题](../../requirements/ISOP-2029/questions.md) · [用例](../../requirements/ISOP-2029/test-cases.md) |
| 2026-09-03 18:31:21 | [ISOP-2028](https://alibaba-international.atlassian.net/browse/ISOP-2028) 合規後台 - 統計數據時間調整 | 两税报、报告摘要、JP/GGR公式和导出 | [设计](../../requirements/ISOP-2028/design.md) · [问题](../../requirements/ISOP-2028/questions.md) · [用例](../../requirements/ISOP-2028/test-cases.md) |
| 2026-09-03 18:30:58 | [ISOP-2027](https://alibaba-international.atlassian.net/browse/ISOP-2027) 管理後台 - KYC 複核功能 | KYC编辑复核、图片、双人权限、同步及审计 | [设计](../../requirements/ISOP-2027/design.md) · [问题](../../requirements/ISOP-2027/questions.md) · [用例](../../requirements/ISOP-2027/test-cases.md) |

<a id="review-20260907-跨需求必须一起核对的地方"></a>

### 跨需求必须一起核对的地方

| 关系 | 已确定的区别/依赖 | 下一步 |
| --- | --- | --- |
| 2041 → 2037 / 2043 / 2028 | 写入先分一般输赢与JP，管理聚合jackpot_payout需映射；合规明细GGR与合规税报GGR不是同一公式 | 用一组供应商一般派彩/JP/贡献已知样本穿透对账；优先回答 [2028 Q-02](../../requirements/ISOP-2028/questions.md) 防止重复扣JP |
| 2022 ↔ 2043 | 管理报表时间/线路与新增JP列需同筛选；邀请好友已按用户决定取消 | 保留已确认node及体育分支规则；2043邀请统计文字列为需修订，不恢复功能 |
| 2037 ↔ 2038 | 2038删独立菜单，JP明细保留在2037的Multi Modal | 不删除JP数据；不要把“展开”实现为列内展开 |
| 2037 ↔ 2028 | 明细无JP用 -，税报无JP为0.00；明细贡献4位，汇总舍入待定 | 分别断言，不能使用一个全局格式/公式替换所有页面 |
| 2032 ↔ 2031 | 投返是自动派发且奖金无过期；通知的1个月期限是另一件事 | 统一事件清单/文案/期限，不能因提示过期扣除奖金 |
| 2030 Jira ↔ Lark ↔ Figma | All入口、Header适用页面、Favorites范围存在版本差异 | 冻结本版设计与页面清单后再判UI符合性 |

<a id="review-20260907-优先请用户补充的业务决定"></a>

### 优先请用户补充的业务决定

1. [2028 Q-02](../../requirements/ISOP-2028/questions.md)：JP已拆分后，有效派彩是否包含JP、具体取什么字段/公式？这决定三份JP报表如何独立对账。
2. [2032 Q-01/02](../../requirements/ISOP-2032/questions.md)：同类型多个游戏规则如何各自封顶和打码，再如何在类型明细展示？门槛已由9月7日晚新版明确为每类型/每规则独立判断及全额计提，不再询问。
3. [2032 Q-03/05](../../requirements/ISOP-2032/questions.md)：返利业务日/迟到单/配置版本，以及停用游戏规则是否回退类型规则、混合奖金投注如何防循环？
4. [2030 Q-01/02](../../requirements/ISOP-2030/questions.md)：All弹层和默认状态、Header页面范围、My删除清单、Favorites是否本版？
5. [2031 Q-01/02](../../requirements/ISOP-2031/questions.md)：三事件范围、派发起算及五页效果已明确；仅需补齐一月边界、消费去重和聚合规则。
6. [2027 Q-01](../../requirements/ISOP-2027/questions.md) 已由用户确认：待审核时不能提交新的KYC；用例改为验证前后端拒绝新提交，不再等待合并/覆盖策略答复。
7. [2041 Q-01](../../requirements/ISOP-2041/questions.md)：9/1历史修复的完整时间边界及依据哪一个时间字段？
8. [2028 Q-01](../../requirements/ISOP-2028/questions.md)：标题仍叫时间调整，本次是否另外包含时间逻辑，还是仅正文JP变更？

每个需求还列出开发应补的接口/字段/版本和少量展示问题；这些不是全部都需要用户回答，也不会阻塞不相关用例。Funky的+8日期与yyyy-MM-dd已从附件确认，免费旋转英语文案也已明确，不重复询问。

<a id="review-20260907-建议组员分工与顺序"></a>

### 建议组员分工与顺序

| 建议工作包 | 内容 | 分工和先后依赖 |
| --- | --- | --- |
| JP后端/数据 | 2041、2028核心金额及2043聚合、2037明细来源 | 一人维护共享独立金额样本；先字段/公式和回填证据，再分派页面核对 |
| 后台UI/导出 | 2043、2037、2028；顺带2038菜单 | 按页面参数化执行，和数据负责人共用样本，不复制三套计算期望 |
| 活动后端/客户端联调 | 2032、2031 | 先返利/批次/账变与通知契约，再打码及客户端事件消费 |
| 客户端UI | 2030、2029 | 小改动2029可先做；2030明确页面与最终稿后分Web/App执行 |
| KYC专项 | 2027 | 后端验证独立状态、权限及原子性；UI验证图片/diff，使用两名不同管理员 |
| 厂商接口 | 2070 | 范围小，可独立验证日期报文；不需要等待JP报表 |

上表是工作分派建议，没有实际通知组员或指派Jira。各用例已留负责人、状态及复测证据列。后端/前端可以按已交付验收点分别开始，不要求整单全部准备完成。

<a id="review-20260907-本轮证据和边界"></a>

### 本轮证据和边界

- 已读取11个Story正文、附件清单与23个子任务；打开3份Lark来源、游戏页Figma画布及KYC/全平台投注记录原型。Funky附件日期说明已人工查看。
- 本轮未逐张核对其余所有截图，金额动画视频未播放逐帧检查；这些视觉细节在各设计中明确保留边界。没有将原型空表或mock结果判为FAT产品缺陷。
- 读取时子任务2062、2056、2057标FAT测试，2058标UAT验收，2054进行中；仅反映Jira状态，不能推导本轮用例通过或主Story全部部署。
- 新增102条设计用例，按风险和实际页面拆分，尚无本轮业务执行证据；ISOP-2022原30个编号无损拆分到独立用例文件。新增用例不是已实现自动化脚本，不改变现有P0范围。
- 未执行业务API/UI测试、未造数或重算、未改Jira或发布评论。文档本地检查结果在当前交接记录。

<a id="review-20260907-2026-09-0820312032更新复审"></a>

### 2026-09-08：2031/2032更新复审

- 2032：规则级门槛替代活动级门槛；三步配置补全；弹窗由不聚合改需聚合，具体聚合粒度待确认；导出具体小节改Xlsx但概述仍写CSV。原C01—C15保留并修订，补C16—C21。
- 2031：本版仅充值成功/Daily Reward/投注返利；从派发起算1个月；五主页面即时动画，其他页返回仅最终图片；首页与My充值均删Details回首页。保留C01—C08并修订，补C09—C12。
- 优先待确认：[2032问题](../../requirements/ISOP-2032/questions.md)中的类型内多规则展示、聚合粒度、文案及导出格式；[2031问题](../../requirements/ISOP-2031/questions.md)中的消费语义、充值返回时点和通知先后竞争。两Story返利文案仍不同，Lark仍有旧领取/无限通知说法。
- 本次读取两个新版Jira、10个新增关联子任务、两份Lark及Step2截图。没有执行活动配置、派发、充值或其他业务测试；原型与附件不作为FAT通过证据。首轮102条为历史统计，本次两需求用例数量以各自文件为准。

<a id="review-20260907-2026-09-08补充isop-2072"></a>

### 2026-09-08：补充ISOP-2072

[报表排程需求](../../requirements/ISOP-2072/design.md) 创建于9月7日21:13，晚于首轮批次快照，单独补充到倒序索引，未改写原11个Story的历史查询结论。核心为BI每5分钟、Pagcor每10分钟且从第2分钟开始，以及指定表/日期重算API；差异/当日全量、跨日修复、切换范围与完成时效待确认。设计、问题和12条未执行用例分别维护；与2022/RisingWave及JP报表联动。


<a id="coverage-20260911"></a>

## 2022—2072：已提交接口与未测范围核对

本文保留开测前盘点快照；随后已按顺序执行2031、2043、2028，当前结果和2032/2037的剩余缺口见[首轮测试](requirement-records-20260907-11.md#test-20260911)。下文“未测”均指盘点时点。

核对日期：2026-09-11。按requirements现有13个需求目录核对，子任务归父需求；不将编号区间中的所有数字虚构为需求。接口来源为backend_api `365c785..b8daa7d`（沿用本期评审基线，最新远端在上一轮已只读核对），对照当前plan.json/api/cases.json、留存执行记录、reports/qa真实批次和旧api/results目录。提交与需求关联以内容对应为依据，不等同于后端代码已部署或正式提测。

结论：**有，重点是2028、2031、2043的新范围，以及2032、2037尚未执行的编辑/导出范围。** 下表“未测”指本仓库未见该变更对应执行证据，不代表其他测试人员一定没有测过。旧结果删除不抹去已测历史，也不把旧文字结论算成当前复测。

<a id="coverage-20260911-已提交但未见对应实测"></a>

### 已提交但未见对应实测

| 需求 | 接口/变更 | 提交依据 | 当前证据与测试缺口 |
| --- | --- | --- | --- |
| 2028 合规报表 | POST /cmpl/report/pagcor/list、/cmpl/report/pagcor/export、/cmpl/report/shop/list、/cmpl/report/shop/export、/cmpl/report/summary/list | cddc218，合并于b8daa7d | 5处新增总GGR/JP贡献，摘要另增JP派奖；无执行计划、无实测报告。[契约评审](../../requirements/ISOP-2028/api/contract-review.md)已列完整路径及公式缺口 |
| 2031 金额动画/到账通知 | GET /promo/notify/change/balance；POST /promo/notify/read/balance | 3797cae、cea06b1、9b03edc、ca3c1c2 | 2处HTTP接口未实现需求执行配置、无实测证据；通知GET及MQTT已给id/ty/sub_ty/balance等结构。已读会消费通知，需本轮专用事件；HTTP通过也不能替代MQTT去重、消费和到期验证 |
| 2043 管理后台JP统计 | GET /admin/reports/venue/node、/admin/reports/game/node、/admin/reports/gameclass/node、/admin/reports/member、/admin/reports/member-daily-game/aggregate | 12311df（2026-09-11） | 5处新增jp_winning，当前cases.json只覆盖两条record查询，不含这5条统计。9月10日测试早于该提交；2022的9月11日查询也未断言这些统计JP字段 |
| 2032 投注返利 | /admin/promo/update；GET /admin/promo/betting/rebate/export | 0bdec54、59844d4 | 编辑和导出未执行；编辑请求块GET与正文POST冲突，导出异步文件获取契约未完整。已测report查询不能证明配置编辑、T+1计算/入账或导出正确 |
| 2037 合规投注明细 | POST /cmpl/record/export | 9e323bb | 列表查询已测，导出未执行；尚缺实际24列文件、顺序/金额/跨页完整性证据 |

2028完整路径统一在其契约评审维护。上述共15个主要HTTP接口的变更/功能范围未见对应实测（5+2+5+2+1），不是15个BUG，也不是15个全部新增的路由。

补充1处关联待确认：3797cae将GET `/promo/notify/list`响应字段`Id`改为`id`；当前未见该字段改动的专项验证。该接口是既有活动通知，可影响2031通知排队及2029免费旋转提示，但没有明确需求编号，不能直接计入任一需求已提测范围。已读接口文档还把正文URL写成`/promo/notify/change/balance`，请求块实际为`/promo/notify/read/balance`，后续先核对路径再消费专用通知。

<a id="coverage-20260911-13个需求逐项结论"></a>

### 13个需求逐项结论

| 需求 | 本次分类 | 说明/依据 |
| --- | --- | --- |
| 2022 | 已部分实测，等待修复 | 两处注单查询已有首轮和限定复核；按用户最新要求暂停复测。[问题与报告](../../requirements/ISOP-2022/bug-review.md)；不列为从未测 |
| 2027 | 已部分实测，仍有覆盖缺口 | KYC复核已有历史API及当前固定UI批次中的API步骤；C18分行联动游戏限制等尚未实现。UAT消息仅请求更新，不等于部署完成；不把准备包算实测。[契约评审](../../requirements/ISOP-2027/api/contract-review.md) |
| 2028 | 新接口字段已提交，未测 | 见上方5处报表/导出 |
| 2029 | 未定位明确的新API交付 | 主范围为免费旋转领取文案；notify/list字段变化仅相关线索，不据此新增整套接口范围 |
| 2030 | 当前限人工UI | 用户已确定H5改版按人工UI，未见本期明确API变更；不因扫描默认API范围重复列待测接口 |
| 2031 | HTTP/MQTT契约已有，未测 | 见上方通知读取、已读及消息结构；动画本身仍人工UI |
| 2032 | 查询历史已测，编辑/导出及闭环未测 | [9月10日记录](requirement-records-20260907-11.md#isop-2032-20260910)保留报表查询/鉴权与金额精度差异；旧原始结果已清理，不能导入当前批次 |
| 2037 | 列表历史已测，导出等未测 | [9月10日记录](requirement-records-20260907-11.md#isop-2037-20260910)保留Multi金额、空值/时间参数问题；旧原始结果已清理，不能说列表从未执行 |
| 2038 | 无本期新接口交付依据 | 范围为删除独立Jackpot菜单，保留投注列表及JP数据；主要人工UI，不因删菜单推断删API |
| 2041 | 后端数据改动，未定位独立验收接口提交 | JP拆分写入/历史回填需源数据与处理证据。2037/2043读到字段不等于2041已完成验收 |
| 2043 | 两处列表历史已测，新增5处统计未测 | [9月10日记录](requirement-records-20260907-11.md#isop-2043-20260910)仅覆盖record/bet和record/game；不能代替9月11日新增JP报表断言 |
| 2070 | 未定位本期相关接口文档提交 | Funky Statement Date出站日期格式需厂商沙箱/脱敏报文与实现证据；不是普通后台列表接口 |
| 2072 | 需求要求重算API，尚未定位新契约 | 本期提交清单及全文关键词未匹配指定表/日期重算新接口；已有报表查询不等于排程/重算已交付。不能把任意旧adjust接口当它的新API |

当前保留的reports/qa实际执行主要为2022两批、2027一批；2027 team-ready为manual-preparation。2032/2037/2043的旧api/results中无原始批次，历史已测事实依据各自日期记录，证据退出边界保持。

<a id="coverage-20260911-后续测试顺序"></a>

### 后续测试顺序

优先补2031通知读取、2043五处JP统计、2028三处报表查询的结构/明确字段断言；写入已读、配置编辑和导出任务按各自作用准备本轮数据和文件获取流程。未知金额公式或缺少独立样本只影响对应断言，不把全部接口都拦住。2032/2037已有查询可按当前版本补证据，但需与首次未测的编辑/导出分开报告。2022继续等修复。

本次仅核对资产与证据，未登录业务、未执行业务API/UI、未发Telegram或提交BUG。文档检查与差异检查通过，不计业务测试结果。


<a id="test-20260911"></a>

## 新交付接口首轮测试：2026-09-11

按用户“一个一个开始测”指令，依次执行2031、2043、2028，随后核对2032、2037尚未测的编辑/导出条件。FAT每个需求独立登录；接口文档基线b8daa7d，部署版本未提供，不能视为已核验部署。2022按用户要求等待修复。

<a id="test-20260911-实际结果"></a>

### 实际结果

| 需求 | 通过 | 失败 | 未执行 | 本轮结论与中文报告 |
| --- | --- | --- | --- | --- |
| 2031 到账通知 | 2 | 2 | 2 | 报告（原始证据已于2026-09-16清理；仅保留历史结论）：未登录/无效登录凭据均被拒绝；正常查询成功，但通知列表为null，事件字段和金额无法验证 |
| 2043 JP统计 | 18 | 2 | 1 | 报告（原始证据已于2026-09-16清理；仅保留历史结论）：五处统计鉴权通过，四处的列表与JP金额字段通过；会员统计列表为null；独立金额对账未执行 |
| 2028 合规报表 | 12 | 0 | 3 | 报告（原始证据已于2026-09-16清理；仅保留历史结论）：三处报表结构、新增字段与鉴权通过；两个导出及独立公式未执行 |

以上均无执行错误。计数按测试组合，不是BUG数量；部分接口通过不代表需求整体验收。原始result.json与冻结计划在各批次同目录。中文展示调整未修改原始结果或快照。

<a id="test-20260911-需要看的问题"></a>

### 需要看的问题

1. **2031通知列表为空值**：`GET /promo/notify/change/balance`返回HTTP 200、业务成功，但`data.list=null`，与文档数组类型不符。当前没有已冻结的本轮通知样本，不能据此认定到账通知丢失；事件字段检查失败是同一无列表前置导致，不能当成第二个独立BUG。
2. **2043会员统计列表为空值**：`GET /admin/reports/member`在9月8日至10日固定窗口返回HTTP 200、业务成功、`data.d=null`。列表结构和JP字段检查因此失败。未做会员源数据独立对账，不能直接断言记录漏查或JP算错。其他四处列表分别取得19、20、20、9条记录并验证`jp_winning`为有限十进制字符串；未验证跨页、非零样本与源数据金额一致性。
3. **2028当前仅证实字段已返回**：Pagcor/门店报表检查总GGR与JP贡献，摘要检查总GGR、JP贡献、JP派奖的字符串类型。列表金额额外检查可解析为有限十进制；摘要本轮没有检查两位小数格式。税率、舍入、独立源金额未冻结，未验证计算正确性。Pagcor文档表格写code=0，示例写status=true，本轮按示例断言并实测通过，文档内部差异仍在。

<a id="test-20260911-尚未执行的具体范围"></a>

### 尚未执行的具体范围

| 需求 | 未执行范围 | 缺少的条件 |
| --- | --- | --- |
| 2031 | 已读消费、MQTT重复/过期与动画联动 | 本轮专用到账事件、订阅/重放条件；已读正文路径与请求块还存在冲突。本轮未消费通知 |
| 2043 | JP独立聚合对账 | 冻结源记录、截止点和独立预期金额；字段存在不能代替对账 |
| 2028 | Pagcor/门店实际导出、GGR和税额公式 | 导出topic订阅与分片完成/文件组装契约，以及源金额/税率/舍入基准 |
| 2032 | 配置编辑、返利实际导出 | 编辑GET/POST冲突及活动32/40映射尚未消除，缺少本轮专用活动；导出只提供topic_id和ok响应，缺少文件获取流程。详见[问题](../../requirements/ISOP-2032/questions.md)Q-11、Q-13 |
| 2037 | 实际导出24栏、顺序/金额/跨页完整性 | 异步topic文件获取条件不足；最新文档CSV表头实际为23项，与需求C10的24栏不一致，需先明确缺少的列。详见[问题](../../requirements/ISOP-2037/questions.md)Q-04 |

2032、2037本轮完成契约复核，**没有发送其编辑/导出请求，也没有新执行批次**。现有查询的9月10日历史记录不能填充这次未测导出结果。全仓文档可找到部分MQTT导出分片说明，但尚未找到本环境订阅鉴权/连接与这两项文件完成判定的完整契约；不猜topic或借用他人任务。

<a id="test-20260911-执行资产与验证"></a>

### 执行资产与验证

2031、2043新增统计、2028查询已纳入各自plan.json和api/data-cases.csv，使用统一`run-requirement.py`执行。2043旧record查询保留在legacy_acceptance，旧API CLI资产不删除；本轮计划只覆盖新增统计。共享只读探针有固定路由白名单，客户端和合规后台分别fresh登录，登录失败不重复尝试。未扩展P0写范围。

本轮没有投注、配置修改、通知消费、导出任务、数据库写入、BUG提交或群消息。候选问题留本地，BUG建单仍需用户确认。后续先补专用通知和导出取文件条件，再执行相应组合；空列表问题结合独立样本复核，2022保持暂停。

本地验证：三个计划离线导出通过；`npm run check`通过（303项单测及文档/资产/语法检查）。首次沙箱执行有三项localhost监听受限，提升执行权限后通过。三个中文报告证据链接已检查，原始JSON和冻结快照保持。上述本地检查不替代业务实测。


<a id="isop-2032-20260910"></a>

## ISOP-2032：2026-09-10 FAT 接口测试记录

> 留存说明（2026-09-11）：本文是原日期的文字结论。用户已授权删除旧结果、扫描和临时脚本，文内旧路径只表示历史来源，不能作为当前可复核/可导入证据；当前入口与保留范围见[清理记录](../project-cleanup-2026-09-11.md)。

[正反例数据](../../requirements/ISOP-2032/api/cases.json) · [契约评审](../../requirements/ISOP-2032/api/contract-review.md) · [验收用例](../../requirements/ISOP-2032/test-cases.md)

执行环境沿用设计FAT；部署版本未提供。先生成数据，完成本地断言校验，再执行真实API。复用本轮新登录，未使用旧token；未编辑配置、审批会员、创建投注、派奖或导出任务。

按组合ID取本轮最新结果：**8个已调用组合，PASS 7，FAIL 1**。FAIL表示当前断言不满足，分类见下表；不能全部视为已确认产品缺陷。另有21条验收闭环因契约/样本/UI未完成保留BLOCKED，未用查询PASS完成整单。

<a id="isop-2032-20260910-发现与处理"></a>

### 发现与处理

| 编号 | 分类 | 组合ID | 实际证据 | 后续处理 |
| --- | --- | --- | --- | --- |
| F-01 | 精度/契约待确认，非已确认产品缺陷 | rebate-detail-sums | 同一报表行bonus=0.4000、multiple_amount=0.40；conf对应金额均为0.405，严格相等断言失败，其余7行本次诊断相等 | Q-05确认截断/舍入方式及发生层级，再分别断言实派与展示；不能擅加误差将其改PASS |
| F-02 | 查询通过的边界 | rebate-report-state-0/1/3/4、rebate-detail-fields | 查询结构与明细金额字段通过；请求/响应state定义仍冲突 | 不证明需手动领取，也不证明T+1计算、入账、幂等正确 |
| F-03 | 已修正测试识别并复测通过 | auth-missing / auth-invalid | HTTP200、status=false、data="token"符合FAT鉴权拒绝 | 不是越权漏洞；保留首次错误识别与复测证据 |

<a id="isop-2032-20260910-执行与复测"></a>

### 执行与复测

| 轮次 | 命令/范围 | 证据 |
| --- | --- | --- |
| 首次 | python3 scripts/run-requirement-api.py ISOP-2027 ISOP-2032 ISOP-2037 ISOP-2043 --env .env.fat --execute --insecure | results/20260910T064048360549Z/report.md与result.json |
| 定向复测 | 同命令增加 --only auth-missing auth-invalid review-list-state-1 rebate-detail-sums；只选本需求命中的组合 | results/20260910T064317776852Z/report.md与result.json |

首次受沙箱网络限制导致登录失败的记录另存于results/20260910T064035891256Z，未发送业务请求；解除网络限制后才是上表真实执行。首次失败未覆盖，复测仅更新相同组合的最新结论。结果目录是本地忽略产物，此文件保存脱敏长期结论，未上传Jira评论或缺陷。


<a id="isop-2037-20260910"></a>

## ISOP-2037：2026-09-10 FAT 接口测试记录

> 留存说明（2026-09-11）：本文是原日期的文字结论。用户已授权删除旧结果、扫描和临时脚本，文内旧路径只表示历史来源，不能作为当前可复核/可导入证据；当前入口与保留范围见[清理记录](../project-cleanup-2026-09-11.md)。

[正反例数据](../../requirements/ISOP-2037/api/cases.json) · [契约评审](../../requirements/ISOP-2037/api/contract-review.md) · [验收用例](../../requirements/ISOP-2037/test-cases.md)

执行环境沿用设计FAT；部署版本未提供。先生成数据，完成本地断言校验，再执行真实API。复用本轮新登录，未使用旧token；未编辑配置、审批会员、创建投注、派奖或导出任务。

按组合ID取本轮最新结果：**10个已调用组合，PASS 7，FAIL 3**。FAIL表示当前断言不满足，分类见下表；不能全部视为已确认产品缺陷。另有11条验收闭环因契约/样本/UI未完成保留BLOCKED，未用查询PASS完成整单。

<a id="isop-2037-20260910-发现与处理"></a>

### 发现与处理

| 编号 | 分类 | 组合ID | 实际证据 | 后续处理 |
| --- | --- | --- | --- | --- |
| F-01 | 金额不一致，待核对样本/部署 | game-jp-99 | 一笔Multi主单jp_winning=4200000.01000000；两明细100000.00000000+500000.00000000=600000.00000000，相差3600000.01。另一笔600000.05与明细相等 | 不修改预期、不调整源数据；核对主单与奖池明细来源/回填 |
| F-02 | 空结果契约差异 | game-jp-2 | HTTP200/status=true，t=0/s=0，但data.d=null；文档为array | 保留结构FAIL；不能认为Minor筛选业务已验证 |
| F-03 | 必填参数契约差异 | game-missing-time | 缺少全部时间范围，返回HTTP200/status=true/data=null | 需确认是合法空结果还是缺少必填校验，不把成功包装当明确拒绝 |
| F-04 | 已修正测试识别并复测通过 | auth-missing / auth-invalid | 精确识别FAT data="token"拒绝标记 | 无数据泄露证据，非权限缺陷 |

<a id="isop-2037-20260910-执行与复测"></a>

### 执行与复测

| 轮次 | 命令/范围 | 证据 |
| --- | --- | --- |
| 首次 | python3 scripts/run-requirement-api.py ISOP-2027 ISOP-2032 ISOP-2037 ISOP-2043 --env .env.fat --execute --insecure | results/20260910T064048360549Z/report.md与result.json |
| 定向复测 | 同命令增加 --only auth-missing auth-invalid review-list-state-1 rebate-detail-sums；只选本需求命中的组合 | results/20260910T064317776852Z/report.md与result.json |

首次受沙箱网络限制导致登录失败的记录另存于results/20260910T064035891256Z，未发送业务请求；解除网络限制后才是上表真实执行。首次失败未覆盖，复测仅更新相同组合的最新结论。结果目录是本地忽略产物，此文件保存脱敏长期结论，未上传Jira评论或缺陷。


<a id="isop-2043-20260910"></a>

## ISOP-2043：2026-09-10 FAT 接口测试记录

> 留存说明（2026-09-11）：本文是原日期的文字结论。用户已授权删除旧结果、扫描和临时脚本，文内旧路径只表示历史来源，不能作为当前可复核/可导入证据；当前入口与保留范围见[清理记录](../project-cleanup-2026-09-11.md)。

[正反例数据](../../requirements/ISOP-2043/api/cases.json) · [契约评审](../../requirements/ISOP-2043/api/contract-review.md) · [验收用例](../../requirements/ISOP-2043/test-cases.md)

执行环境沿用设计FAT；部署版本未提供。先生成数据，完成本地断言校验，再执行真实API。复用本轮新登录，未使用旧token；未编辑配置、审批会员、创建投注、派奖或导出任务。

按组合ID取本轮最新结果：**22个已调用组合，PASS 16，FAIL 6**。FAIL表示当前断言不满足，分类见下表；不能全部视为已确认产品缺陷。另有9条验收闭环因契约/样本/UI未完成保留BLOCKED，未用查询PASS完成整单。

<a id="isop-2043-20260910-发现与处理"></a>

### 发现与处理

| 编号 | 分类 | 组合ID | 实际证据 | 后续处理 |
| --- | --- | --- | --- | --- |
| F-01 | 金额不一致，待核对样本/部署 | bet-jp-99 / game-jp-99 | 财务与游戏投注入口均未通过Multi金额加总断言；关联2037同查询窗口样本 | 两入口共用逻辑，不能当作两个独立数据源验证正确 |
| F-02 | 空结果契约差异 | bet-jp-2 / game-jp-2 | HTTP200/status=true，data.d不是array | 不放宽结构断言，不将空数据算类型/金额通过 |
| F-03 | 必填参数契约差异 | bet-missing-time / game-missing-time | 缺少两组时间范围仍业务成功，data=null | 确认时间参数校验契约 |
| F-04 | 已修正测试识别并复测通过 | auth-missing / auth-invalid | 精确识别FAT data="token"拒绝标记 | 不以首次测试识别失败宣称越权 |

<a id="isop-2043-20260910-执行与复测"></a>

### 执行与复测

| 轮次 | 命令/范围 | 证据 |
| --- | --- | --- |
| 首次 | python3 scripts/run-requirement-api.py ISOP-2027 ISOP-2032 ISOP-2037 ISOP-2043 --env .env.fat --execute --insecure | results/20260910T064048360549Z/report.md与result.json |
| 定向复测 | 同命令增加 --only auth-missing auth-invalid review-list-state-1 rebate-detail-sums；只选本需求命中的组合 | results/20260910T064317776852Z/report.md与result.json |

首次受沙箱网络限制导致登录失败的记录另存于results/20260910T064035891256Z，未发送业务请求；解除网络限制后才是上表真实执行。首次失败未覆盖，复测仅更新相同组合的最新结论。结果目录是本地忽略产物，此文件保存脱敏长期结论，未上传Jira评论或缺陷。

