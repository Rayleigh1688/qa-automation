# 需求历史评审与接口盘点（2026-09-07—2026-09-11）

2026-09-15集中整理早期评审。2026-11-27按用户授权退出旧日期报告、执行明细和判定。保留需求来源、接口盘点与原章节定位。

[需求索引](../../requirements/README.md) · [历史归档](../../requirements/history/README.md)

## 原记录索引

| 原位置 | 合并位置 | 原Markdown SHA-256（合并前） |
| --- | --- | --- |
| `requirements/review-summary.md` | [历史章节](#review-20260907) | `6ec36562693b9b55a831c6d1063d7dd03e54e01bd28a67758a2aa001bc70f633` |
| `requirements/api-coverage-review-20260911.md` | [历史章节](#coverage-20260911) | `79150fd43d0d5ef06f81852f31ff36a049b0c64f329cbdfa89f73457a5060092` |

<a id="review-20260907"></a>

## ISOP-2022 之后的新 Story：评审与分派

首轮评审快照：2026-09-07（UTC+8）；ISOP-2031/2032于2026-09-08复审，更新见下。本批为需求梳理和测试设计，不是业务验收报告。逐条可分派用例见 [需求索引](../../requirements/README.md)，用例设计和前置条件维护在各需求目录。

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
| 2026-09-07 16:47:15 | [ISOP-2070](https://alibaba-international.atlassian.net/browse/ISOP-2070) Funky 時間回傳問題 | Funky纯日期、+8日界、重试 | [设计](../../requirements/history/through-ISOP-2072/ISOP-2070/design.md) · [问题](../../requirements/history/through-ISOP-2072/ISOP-2070/questions.md) · [用例](../../requirements/history/through-ISOP-2072/ISOP-2070/test-cases.md) |
| 2026-09-07 00:20:36 | [ISOP-2043](https://alibaba-international.atlassian.net/browse/ISOP-2043) 管理後台 - 新增 JP 資訊 | 会员/游戏/财务五组JP表单 | [设计](../../requirements/history/through-ISOP-2072/ISOP-2043/design.md) · [问题](../../requirements/history/through-ISOP-2072/ISOP-2043/questions.md) · [用例](../../requirements/history/through-ISOP-2072/ISOP-2043/test-cases.md) |
| 2026-09-07 00:06:12 | [ISOP-2041](https://alibaba-international.atlassian.net/browse/ISOP-2041) JP 注單寫入方式調整 | JP字段拆分、历史修复、资金不变 | [设计](../../requirements/history/through-ISOP-2072/ISOP-2041/design.md) · [问题](../../requirements/history/through-ISOP-2072/ISOP-2041/questions.md) · [用例](../../requirements/history/through-ISOP-2072/ISOP-2041/test-cases.md) |
| 2026-09-05 00:32:02 | [ISOP-2038](https://alibaba-international.atlassian.net/browse/ISOP-2038) 合規後台 - 移除 Jackpot 記錄選單 | 菜单和旧路由移除 | [设计](../../requirements/history/through-ISOP-2072/ISOP-2038/design.md) · [问题](../../requirements/history/through-ISOP-2072/ISOP-2038/questions.md) · [用例](../../requirements/history/through-ISOP-2072/ISOP-2038/test-cases.md) |
| 2026-09-05 00:16:03 | [ISOP-2037](https://alibaba-international.atlassian.net/browse/ISOP-2037) 合規後台 - 全平台投注紀錄增加欄位 | 四JP列、Multi、类型筛选、24列CSV | [设计](../../requirements/history/through-ISOP-2072/ISOP-2037/design.md) · [问题](../../requirements/history/through-ISOP-2072/ISOP-2037/questions.md) · [用例](../../requirements/history/through-ISOP-2072/ISOP-2037/test-cases.md) |
| 2026-09-03 18:39:25 | [ISOP-2032](https://alibaba-international.atlassian.net/browse/ISOP-2032) 用戶端 - 投注返利活動 | 活动配置、返利计算、派发/流水、通知、报表 | [设计](../../requirements/history/through-ISOP-2072/ISOP-2032/design.md) · [问题](../../requirements/history/through-ISOP-2072/ISOP-2032/questions.md) · [用例](../../requirements/history/through-ISOP-2072/ISOP-2032/test-cases.md) |
| 2026-09-03 18:38:52 | [ISOP-2031](https://alibaba-international.atlassian.net/browse/ISOP-2031) 用戶端 - 新增金額動畫效果 | 事件范围、通知去重/到期、金额动画 | [设计](../../requirements/history/through-ISOP-2072/ISOP-2031/design.md) · [问题](../../requirements/history/through-ISOP-2072/ISOP-2031/questions.md) · [用例](../../requirements/history/through-ISOP-2072/ISOP-2031/test-cases.md) |
| 2026-09-03 18:37:08 | [ISOP-2030](https://alibaba-international.atlassian.net/browse/ISOP-2030) 用戶端 - 遊戲頁面改版 | Header、Games、Rewards、Filcoin、My | [设计](../../requirements/history/through-ISOP-2072/ISOP-2030/design.md) · [问题](../../requirements/history/through-ISOP-2072/ISOP-2030/questions.md) · [用例](../../requirements/history/through-ISOP-2072/ISOP-2030/test-cases.md) |
| 2026-09-03 18:36:44 | [ISOP-2029](https://alibaba-international.atlassian.net/browse/ISOP-2029) 用戶端 - 免費旋轉領取文案調整 | 领取成功文案、两按钮、既有流程回归 | [设计](../../requirements/history/through-ISOP-2072/ISOP-2029/design.md) · [问题](../../requirements/history/through-ISOP-2072/ISOP-2029/questions.md) · [用例](../../requirements/history/through-ISOP-2072/ISOP-2029/test-cases.md) |
| 2026-09-03 18:31:21 | [ISOP-2028](https://alibaba-international.atlassian.net/browse/ISOP-2028) 合規後台 - 統計數據時間調整 | 两税报、报告摘要、JP/GGR公式和导出 | [设计](../../requirements/history/through-ISOP-2072/ISOP-2028/design.md) · [问题](../../requirements/history/through-ISOP-2072/ISOP-2028/questions.md) · [用例](../../requirements/history/through-ISOP-2072/ISOP-2028/test-cases.md) |
| 2026-09-03 18:30:58 | [ISOP-2027](https://alibaba-international.atlassian.net/browse/ISOP-2027) 管理後台 - KYC 複核功能 | KYC编辑复核、图片、双人权限、同步及审计 | [设计](../../requirements/history/through-ISOP-2072/ISOP-2027/design.md) · [问题](../../requirements/history/through-ISOP-2072/ISOP-2027/questions.md) · [用例](../../requirements/history/through-ISOP-2072/ISOP-2027/test-cases.md) |

<a id="review-20260907-跨需求必须一起核对的地方"></a>

### 跨需求必须一起核对的地方

| 关系 | 已确定的区别/依赖 | 下一步 |
| --- | --- | --- |
| 2041 → 2037 / 2043 / 2028 | 写入先分一般输赢与JP，管理聚合jackpot_payout需映射；合规明细GGR与合规税报GGR不是同一公式 | 用一组供应商一般派彩/JP/贡献已知样本穿透对账；优先回答 [2028 Q-02](../../requirements/history/through-ISOP-2072/ISOP-2028/questions.md) 防止重复扣JP |
| 2022 ↔ 2043 | 管理报表时间/线路与新增JP列需同筛选；邀请好友已按用户决定取消 | 保留已确认node及体育分支规则；2043邀请统计文字列为需修订，不恢复功能 |
| 2037 ↔ 2038 | 2038删独立菜单，JP明细保留在2037的Multi Modal | 不删除JP数据；不要把“展开”实现为列内展开 |
| 2037 ↔ 2028 | 明细无JP用 -，税报无JP为0.00；明细贡献4位，汇总舍入待定 | 分别断言，不能使用一个全局格式/公式替换所有页面 |
| 2032 ↔ 2031 | 投返是自动派发且奖金无过期；通知的1个月期限是另一件事 | 统一事件清单/文案/期限，不能因提示过期扣除奖金 |
| 2030 Jira ↔ Lark ↔ Figma | All入口、Header适用页面、Favorites范围存在版本差异 | 冻结本版设计与页面清单后再判UI符合性 |

<a id="review-20260907-优先请用户补充的业务决定"></a>

### 优先请用户补充的业务决定

1. [2028 Q-02](../../requirements/history/through-ISOP-2072/ISOP-2028/questions.md)：JP已拆分后，有效派彩是否包含JP、具体取什么字段/公式？这决定三份JP报表如何独立对账。
2. [2032 Q-01/02](../../requirements/history/through-ISOP-2072/ISOP-2032/questions.md)：同类型多个游戏规则如何各自封顶和打码，再如何在类型明细展示？门槛已由9月7日晚新版明确为每类型/每规则独立判断及全额计提，不再询问。
3. [2032 Q-03/05](../../requirements/history/through-ISOP-2072/ISOP-2032/questions.md)：返利业务日/迟到单/配置版本，以及停用游戏规则是否回退类型规则、混合奖金投注如何防循环？
4. [2030 Q-01/02](../../requirements/history/through-ISOP-2072/ISOP-2030/questions.md)：All弹层和默认状态、Header页面范围、My删除清单、Favorites是否本版？
5. [2031 Q-01/02](../../requirements/history/through-ISOP-2072/ISOP-2031/questions.md)：三事件范围、派发起算及五页效果已明确；仅需补齐一月边界、消费去重和聚合规则。
6. [2027 Q-01](../../requirements/history/through-ISOP-2072/ISOP-2027/questions.md) 已由用户确认：待审核时不能提交新的KYC；用例改为验证前后端拒绝新提交，不再等待合并/覆盖策略答复。
7. [2041 Q-01](../../requirements/history/through-ISOP-2072/ISOP-2041/questions.md)：9/1历史修复的完整时间边界及依据哪一个时间字段？
8. [2028 Q-01](../../requirements/history/through-ISOP-2072/ISOP-2028/questions.md)：标题仍叫时间调整，本次是否另外包含时间逻辑，还是仅正文JP变更？

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
- 优先待确认：[2032问题](../../requirements/history/through-ISOP-2072/ISOP-2032/questions.md)中的类型内多规则展示、聚合粒度、文案及导出格式；[2031问题](../../requirements/history/through-ISOP-2072/ISOP-2031/questions.md)中的消费语义、充值返回时点和通知先后竞争。两Story返利文案仍不同，Lark仍有旧领取/无限通知说法。
- 本次读取两个新版Jira、10个新增关联子任务、两份Lark及Step2截图。没有执行活动配置、派发、充值或其他业务测试；原型与附件不作为FAT通过证据。首轮102条为历史统计，本次两需求用例数量以各自文件为准。

<a id="review-20260907-2026-09-08补充isop-2072"></a>

### 2026-09-08：补充ISOP-2072

[报表排程需求](../../requirements/history/through-ISOP-2072/ISOP-2072/design.md) 创建于9月7日21:13，晚于首轮批次快照，单独补充到倒序索引，未改写原11个Story的历史查询结论。核心为BI每5分钟、Pagcor每10分钟且从第2分钟开始，以及指定表/日期重算API；差异/当日全量、跨日修复、切换范围与完成时效待确认。设计、问题和12条未执行用例分别维护；与2022/RisingWave及JP报表联动。


<a id="coverage-20260911"></a>

## 2022—2072：已提交接口与范围核对

来源为 2026-09-11 对 13 项需求及 Bruno `backend_api` 的静态盘点，接口基线为 `365c785..b8daa7d`。提交与需求的关联依据文档内容。

<a id="coverage-20260911-已提交但未见对应实测"></a>

### 接口文档增量

| 需求 | 接口/变更 | 提交依据 | 验收关注 |
| --- | --- | --- | --- |
| 2028 合规报表 | POST /cmpl/report/pagcor/list、/cmpl/report/pagcor/export、/cmpl/report/shop/list、/cmpl/report/shop/export、/cmpl/report/summary/list | cddc218，合并于b8daa7d | 总GGR、JP贡献、摘要JP派奖、独立计算和导出。见[契约评审](../../requirements/history/through-ISOP-2072/ISOP-2028/api/contract-review.md)。 |
| 2031 金额动画/到账通知 | GET /promo/notify/change/balance、POST /promo/notify/read/balance | 3797cae、cea06b1、9b03edc、ca3c1c2 | 事件字段、通知消费、MQTT去重和到期。已读接口的正文与请求块路径冲突，消费前先复核。 |
| 2043 管理后台JP统计 | GET /admin/reports/venue/node、/admin/reports/game/node、/admin/reports/gameclass/node、/admin/reports/member、/admin/reports/member-daily-game/aggregate | 12311df | `jp_winning` 字段及与注单源数据的独立对账。 |
| 2032 投注返利 | /admin/promo/update、GET /admin/promo/betting/rebate/export | 0bdec54、59844d4 | 编辑请求块与正文方法冲突。补配置生效、派发、导出取文件契约。 |
| 2037 合规投注明细 | POST /cmpl/record/export | 9e323bb | 核对24列要求、文件接收、排序及跨页金额。 |

补充关联线索：3797cae 将活动通知 `GET /promo/notify/list` 的 `Id` 改为 `id`，与2031和2029的关联仍需按实际调用确认。

<a id="coverage-20260911-13个需求逐项结论"></a>

### 13个需求逐项范围

| 需求 | 范围 |
| --- | --- |
| 2022 | 注单统计时间、体育切表及查询契约。 |
| 2027 | KYC复核、权限边界和分行联动。 |
| 2028 | 合规查询、导出及独立公式。 |
| 2029 | 免费旋转领取文案与通知。 |
| 2030 | H5改版人工UI范围。 |
| 2031 | 通知读取、已读、MQTT与动画。 |
| 2032 | 返利配置、计算、入账、报表和导出。 |
| 2037 | 投注明细、JP类型和文件导出。 |
| 2038 | 删除独立Jackpot菜单，保留注单的JP数据。 |
| 2041 | JP拆分写入与历史回填。 |
| 2043 | 注单与统计的JP字段、独立金额对账。 |
| 2070 | Funky出站日期格式和厂商对照。 |
| 2072 | 排程与指定表、日期重算，使用当前专用契约。 |

<a id="coverage-20260911-后续测试顺序"></a>

### 接口执行前置

写入已读、配置编辑和导出按要求准备独立样本、对应的契约和证据来源。查询结构、金额公式和真实文件按各自用例验证。冻结环境版本后按各需求用例执行。

<a id="test-20260911"></a>
<a id="test-20260911-实际结果"></a>
<a id="test-20260911-需要看的问题"></a>
<a id="test-20260911-尚未执行的具体范围"></a>
<a id="test-20260911-执行资产与验证"></a>

## 2026-09-11首轮报告退出

2026-09-11 的 2031、2043、2028 执行报告、实际结果与明细于 2026-11-27 全部退出当前文档。

<a id="isop-2032-20260910"></a>
<a id="isop-2032-20260910-发现与处理"></a>
<a id="isop-2032-20260910-执行与复测"></a>

## ISOP-2032 FAT记录退出

2026-09-10 的 2032 执行报告、实际结果与明细于 2026-11-27 全部退出当前文档。

<a id="isop-2037-20260910"></a>
<a id="isop-2037-20260910-发现与处理"></a>
<a id="isop-2037-20260910-执行与复测"></a>

## ISOP-2037 FAT记录退出

2026-09-10 的 2037 执行报告、实际结果与明细于 2026-11-27 全部退出当前文档。

<a id="isop-2043-20260910"></a>
<a id="isop-2043-20260910-发现与处理"></a>
<a id="isop-2043-20260910-执行与复测"></a>

## ISOP-2043 FAT记录退出

2026-09-10 的 2043 执行报告、实际结果与明细于 2026-11-27 全部退出当前文档。
