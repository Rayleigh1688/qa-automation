# ISOP-2022 之后的新 Story：评审与分派

首轮评审快照：2026-09-07（UTC+8）；ISOP-2031/2032于2026-09-08复审，更新见下。本批为需求梳理和测试设计，不是业务验收报告。逐条可分派用例见 [需求索引](README.md)，当前执行状态只维护在各自用例文件。

## 查询范围与完整性

已能访问用户提供的 [Jira项目列表](https://alibaba-international.atlassian.net/jira/software/projects/ISOP/list?jql=project%20%3D%20ISOP%20ORDER%20BY%20created%20DESC%2C%20cf%5B10019%5D%20ASC)。使用Jira连接器按Story类型和创建时间查询，避免把后建的子任务当成新需求，也不只按编号大小筛选。

```jql
project = ISOP AND issuetype = Story
AND created >= "2026-09-02 22:17"
ORDER BY created DESC, key DESC
```

边界Story ISOP-2022实际创建于`2026-09-02T22:17:31.609+0800`；按完整创建时间排除基准及更早项。返回一页且isLast=true，无后续页；剔除基准后共11个Story，最新为ISOP-2070。覆盖的是本次读取快照，不包含之后新建或更新的需求。11个Story关联的23个子任务也已读取，正文为空、未见评论补充。

## 创建时间倒序清单

| 创建时间（UTC+8） | Story | 首轮审阅范围 | 分派入口 |
| --- | --- | --- | --- |
| 2026-09-07 16:47:15 | [ISOP-2070](https://alibaba-international.atlassian.net/browse/ISOP-2070) Funky 時間回傳問題 | Funky纯日期、+8日界、重试 | [设计](ISOP-2070/design.md) · [问题](ISOP-2070/questions.md) · [用例](ISOP-2070/test-cases.md) |
| 2026-09-07 00:20:36 | [ISOP-2043](https://alibaba-international.atlassian.net/browse/ISOP-2043) 管理後台 - 新增 JP 資訊 | 会员/游戏/财务五组JP表单 | [设计](ISOP-2043/design.md) · [问题](ISOP-2043/questions.md) · [用例](ISOP-2043/test-cases.md) |
| 2026-09-07 00:06:12 | [ISOP-2041](https://alibaba-international.atlassian.net/browse/ISOP-2041) JP 注單寫入方式調整 | JP字段拆分、历史修复、资金不变 | [设计](ISOP-2041/design.md) · [问题](ISOP-2041/questions.md) · [用例](ISOP-2041/test-cases.md) |
| 2026-09-05 00:32:02 | [ISOP-2038](https://alibaba-international.atlassian.net/browse/ISOP-2038) 合規後台 - 移除 Jackpot 記錄選單 | 菜单和旧路由移除 | [设计](ISOP-2038/design.md) · [问题](ISOP-2038/questions.md) · [用例](ISOP-2038/test-cases.md) |
| 2026-09-05 00:16:03 | [ISOP-2037](https://alibaba-international.atlassian.net/browse/ISOP-2037) 合規後台 - 全平台投注紀錄增加欄位 | 四JP列、Multi、类型筛选、24列CSV | [设计](ISOP-2037/design.md) · [问题](ISOP-2037/questions.md) · [用例](ISOP-2037/test-cases.md) |
| 2026-09-03 18:39:25 | [ISOP-2032](https://alibaba-international.atlassian.net/browse/ISOP-2032) 用戶端 - 投注返利活動 | 活动配置、返利计算、派发/流水、通知、报表 | [设计](ISOP-2032/design.md) · [问题](ISOP-2032/questions.md) · [用例](ISOP-2032/test-cases.md) |
| 2026-09-03 18:38:52 | [ISOP-2031](https://alibaba-international.atlassian.net/browse/ISOP-2031) 用戶端 - 新增金額動畫效果 | 事件范围、通知去重/到期、金额动画 | [设计](ISOP-2031/design.md) · [问题](ISOP-2031/questions.md) · [用例](ISOP-2031/test-cases.md) |
| 2026-09-03 18:37:08 | [ISOP-2030](https://alibaba-international.atlassian.net/browse/ISOP-2030) 用戶端 - 遊戲頁面改版 | Header、Games、Rewards、Filcoin、My | [设计](ISOP-2030/design.md) · [问题](ISOP-2030/questions.md) · [用例](ISOP-2030/test-cases.md) |
| 2026-09-03 18:36:44 | [ISOP-2029](https://alibaba-international.atlassian.net/browse/ISOP-2029) 用戶端 - 免費旋轉領取文案調整 | 领取成功文案、两按钮、既有流程回归 | [设计](ISOP-2029/design.md) · [问题](ISOP-2029/questions.md) · [用例](ISOP-2029/test-cases.md) |
| 2026-09-03 18:31:21 | [ISOP-2028](https://alibaba-international.atlassian.net/browse/ISOP-2028) 合規後台 - 統計數據時間調整 | 两税报、报告摘要、JP/GGR公式和导出 | [设计](ISOP-2028/design.md) · [问题](ISOP-2028/questions.md) · [用例](ISOP-2028/test-cases.md) |
| 2026-09-03 18:30:58 | [ISOP-2027](https://alibaba-international.atlassian.net/browse/ISOP-2027) 管理後台 - KYC 複核功能 | KYC编辑复核、图片、双人权限、同步及审计 | [设计](ISOP-2027/design.md) · [问题](ISOP-2027/questions.md) · [用例](ISOP-2027/test-cases.md) |

## 跨需求必须一起核对的地方

| 关系 | 已确定的区别/依赖 | 下一步 |
| --- | --- | --- |
| 2041 → 2037 / 2043 / 2028 | 写入先分一般输赢与JP，管理聚合jackpot_payout需映射；合规明细GGR与合规税报GGR不是同一公式 | 用一组供应商一般派彩/JP/贡献已知样本穿透对账；优先回答 [2028 Q-02](ISOP-2028/questions.md) 防止重复扣JP |
| 2022 ↔ 2043 | 管理报表时间/线路与新增JP列需同筛选；邀请好友已按用户决定取消 | 保留已确认node及体育分支规则；2043邀请统计文字列为需修订，不恢复功能 |
| 2037 ↔ 2038 | 2038删独立菜单，JP明细保留在2037的Multi Modal | 不删除JP数据；不要把“展开”实现为列内展开 |
| 2037 ↔ 2028 | 明细无JP用 -，税报无JP为0.00；明细贡献4位，汇总舍入待定 | 分别断言，不能使用一个全局格式/公式替换所有页面 |
| 2032 ↔ 2031 | 投返是自动派发且奖金无过期；通知的1个月期限是另一件事 | 统一事件清单/文案/期限，不能因提示过期扣除奖金 |
| 2030 Jira ↔ Lark ↔ Figma | All入口、Header适用页面、Favorites范围存在版本差异 | 冻结本版设计与页面清单后再判UI符合性 |

## 优先请用户补充的业务决定

1. [2028 Q-02](ISOP-2028/questions.md)：JP已拆分后，有效派彩是否包含JP、具体取什么字段/公式？这决定三份JP报表如何独立对账。
2. [2032 Q-01/02](ISOP-2032/questions.md)：同类型多个游戏规则如何各自封顶和打码，再如何在类型明细展示？门槛已由9月7日晚新版明确为每类型/每规则独立判断及全额计提，不再询问。
3. [2032 Q-03/05](ISOP-2032/questions.md)：返利业务日/迟到单/配置版本，以及停用游戏规则是否回退类型规则、混合奖金投注如何防循环？
4. [2030 Q-01/02](ISOP-2030/questions.md)：All弹层和默认状态、Header页面范围、My删除清单、Favorites是否本版？
5. [2031 Q-01/02](ISOP-2031/questions.md)：三事件范围、派发起算及五页效果已明确；仅需补齐一月边界、消费去重和聚合规则。
6. [2027 Q-01](ISOP-2027/questions.md) 已由用户确认：待审核时不能提交新的KYC；用例改为验证前后端拒绝新提交，不再等待合并/覆盖策略答复。
7. [2041 Q-01](ISOP-2041/questions.md)：9/1历史修复的完整时间边界及依据哪一个时间字段？
8. [2028 Q-01](ISOP-2028/questions.md)：标题仍叫时间调整，本次是否另外包含时间逻辑，还是仅正文JP变更？

每个需求还列出开发应补的接口/字段/版本和少量展示问题；这些不是全部都需要用户回答，也不会阻塞不相关用例。Funky的+8日期与yyyy-MM-dd已从附件确认，免费旋转英语文案也已明确，不重复询问。

## 建议组员分工与顺序

| 建议工作包 | 内容 | 分工和先后依赖 |
| --- | --- | --- |
| JP后端/数据 | 2041、2028核心金额及2043聚合、2037明细来源 | 一人维护共享独立金额样本；先字段/公式和回填证据，再分派页面核对 |
| 后台UI/导出 | 2043、2037、2028；顺带2038菜单 | 按页面参数化执行，和数据负责人共用样本，不复制三套计算期望 |
| 活动后端/客户端联调 | 2032、2031 | 先返利/批次/账变与通知契约，再打码及客户端事件消费 |
| 客户端UI | 2030、2029 | 小改动2029可先做；2030明确页面与最终稿后分Web/App执行 |
| KYC专项 | 2027 | 后端验证独立状态、权限及原子性；UI验证图片/diff，使用两名不同管理员 |
| 厂商接口 | 2070 | 范围小，可独立验证日期报文；不需要等待JP报表 |

上表是工作分派建议，没有实际通知组员或指派Jira。各用例已留负责人、状态及复测证据列。后端/前端可以按已交付验收点分别开始，不要求整单全部准备完成。

## 本轮证据和边界

- 已读取11个Story正文、附件清单与23个子任务；打开3份Lark来源、游戏页Figma画布及KYC/全平台投注记录原型。Funky附件日期说明已人工查看。
- 本轮未逐张核对其余所有截图，金额动画视频未播放逐帧检查；这些视觉细节在各设计中明确保留边界。没有将原型空表或mock结果判为FAT产品缺陷。
- 读取时子任务2062、2056、2057标FAT测试，2058标UAT验收，2054进行中；仅反映Jira状态，不能推导本轮用例通过或主Story全部部署。
- 新增102条设计用例，按风险和实际页面拆分，尚无本轮业务执行证据；ISOP-2022原30个编号无损拆分到独立用例文件。新增用例不是已实现自动化脚本，不改变现有P0范围。
- 未执行业务API/UI测试、未造数或重算、未改Jira或发布评论。文档本地检查结果在当前交接记录。

## 2026-09-08：2031/2032更新复审

- 2032：规则级门槛替代活动级门槛；三步配置补全；弹窗由不聚合改需聚合，具体聚合粒度待确认；导出具体小节改Xlsx但概述仍写CSV。原C01—C15保留并修订，补C16—C21。
- 2031：本版仅充值成功/Daily Reward/投注返利；从派发起算1个月；五主页面即时动画，其他页返回仅最终图片；首页与My充值均删Details回首页。保留C01—C08并修订，补C09—C12。
- 优先待确认：[2032问题](ISOP-2032/questions.md)中的类型内多规则展示、聚合粒度、文案及导出格式；[2031问题](ISOP-2031/questions.md)中的消费语义、充值返回时点和通知先后竞争。两Story返利文案仍不同，Lark仍有旧领取/无限通知说法。
- 本次读取两个新版Jira、10个新增关联子任务、两份Lark及Step2截图。没有执行活动配置、派发、充值或其他业务测试；原型与附件不作为FAT通过证据。首轮102条为历史统计，本次两需求用例数量以各自文件为准。
