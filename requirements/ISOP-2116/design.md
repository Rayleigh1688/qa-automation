# ISOP-2116：测试设计

[设计](design.md) · [问题](questions.md) · [测试重点](test-cases.md) · [W26评审](../reviews/2026W26-20261006.md)

本期范围是一款drop ball pinoy及其JP数据；已读实际合同为单钱包，金额、退款和JP通知合同仍有具体冲突。本目录整理2026-10-06已读来源及W26评审，本次未重新读取远端来源、未执行业务测试，也未接入执行计划。历史同号资料不自动成为本期合同或通过结论。

## 范围与明确规则

| 项目 | 当前规则与依据 |
| --- | --- |
| 游戏范围 | Jira仅要求drop ball pinoy一款，Pagcor分类为specialty game；附件含其他游戏不扩大接入范围。 |
| 候选编码与路由 | GameList的`Game List!A19:F19`为`10022`、Drop Ball、Live、Jackpot Yes、Bet + Settle、IsEndRound Yes。厂商Live技术路由与Pagcor specialty game属于不同维度，不互相覆盖。候选与正文名称的对应仍依赖[Q-01](questions.md#q-01)。 |
| 钱包模式 | 附件23973实际p1标题、p2§1及p38§3.1.5明确SingleWallet单钱包，由运营商维护钱包并处理厂商逐笔回调；不按“转账钱包”文件名设计双钱包转入／转出。接入版本基线见[Q-01](questions.md#q-01)。 |
| 成功重放与失败重试 | PDF p11§3.1.3要求以`transaction_id`识别已成功请求并返回原成功结果，此前执行失败则重新尝试；p12的`trace_id`只作排障，不能用于去重。 |
| 母子单 | PDF p27要求同母单、不同合法子投注继续处理，适用于未终结回合；不以母单号吞掉后续合法动作。 |
| 回合终态 | PDF p16／p53—54优先以`is_end_round=true`确认终态，此后不再执行同`game_no`的新增投付／退款。此前已成功原交易重发仍重放成功结果，不再变动钱包；终态不把成功重放改成新增动作。 |
| 响应精度与时间 | PDF p13／p28余额最多两位，超出部分截断；p28响应`updated_time`与本次请求值一致。不能改成四舍五入或响应时当前时间。 |
| JP数据来源 | Jira要求从API取得`jackpot seed`／`jackpot contribution`。PDF p17给出`jackpot_seed`、万分比`jackpot_increment`及本笔`jackpot_contribution`；p40—42的`live_info`当前总奖池不能替代seed或本笔贡献。 |

## 合同冲突与影响

以下是已读合同的对照事实，待确认正文与答复只维护在[问题与决定](questions.md)。

| 来源对照 | 影响及关联 |
| --- | --- |
| 23973文件名含“转账钱包”，正文为SingleWallet；2.6.2更新记录2026-06-18，环境版本表日期为2026-05-14。 | 接入钱包与版本基线未冻结，关联[Q-01](questions.md#q-01)。 |
| PDF p21选定DropBallLive示例：`bet_amount=10000`注释“投注100块”，余额变化注释却减100000。原页已视觉核对。 | 金额单位与示例存在矛盾，需独立可计算样本后冻结资金断言，关联[Q-02](questions.md#q-02)。 |
| PDF p17的JP可选回调字段与p40—42当前总奖池含义不同；平台消费字段尚未冻结。 | 缺失、零值及单位需保持区分，不能拿总奖池替换贡献，关联[Q-03](questions.md#q-03)。 |
| PDF p33要求重复退款不再操作钱包并返回退款金额，p34却列3041重复退款；退款引用原成功交易`transaction_id`。 | 原投付与退款的动作身份及重复退款响应需裁决，防止吞退款或重复加款，关联[Q-04](questions.md#q-04)。 |
| PDF p35通知路径为`/Cash/PrizeNotify`，p37重试表写`/Cash/JackpotNotify`。 | 若本期包含JP中奖通知，需要订正路由与入账责任，避免漏通知或与`win_amount`双派，关联[Q-05](questions.md#q-05)。 |

后续按已确认单钱包合同设计投注、分时结算、终态及重放；金额、退款回复和条件纳入的JP通知断言等待对应决定。具体测试重点见[初步测试设计](test-cases.md)。会话成功不能证明真实三方游戏投注。

## 来源与读取边界

| 来源 | 读取情况与定位 |
| --- | --- |
| [ISOP-2116](https://alibaba-international.atlassian.net/browse/ISOP-2116)正文 | 2026-10-06已读完整正文；来源更新快照为2026-10-05，评论总数0。依据为单款范围、Pagcor分类和JP seed／contribution要求；配置及凭据不迁入文档。 |
| ISOP-2198、ISOP-2199 | 2026-10-06已读，正文及评论为空；状态不证明接入或测试完成。 |
| [附件23973.pdf](../../reports/qa/W26/20261006-requirement-review/evidence/attachments/23973.pdf) | 2026-10-06读取相关合同章节，并视觉核对p2、p17、p21、p33、p35、p37。关键定位：p1—2／p38钱包模式，p11—12幂等，p13—17／p21投付与JP，p27—28响应，p31—37退款／通知，p40—42奖池，p53—54终态。不是全页视觉验收。 |
| [附件23974.xlsx](../../reports/qa/W26/20261006-requirement-review/evidence/attachments/23974.xlsx) | 2026-10-06已读`Game List`全部非空行；目标候选定位`A19:F19`。 |
| [SG Drive](https://drive.google.com/file/d/180Ct1MVXogGgyGZMVlYUOKCOJlxbg0wF/view?usp=sharing) | 2026-10-06已核文件为“平台入口.zip”，过大无法预览，ZIP成员未读；不能据此否定已经提供的PDF合同。未登录厂商后台。 |
| [W26评审](../reviews/2026W26-20261006.md) | 本次迁移依据，沿用5项问题；旧`SG-Q01`—`SG-Q05`别名与小写锚点保留在`questions.md`。 |

本次未重新联网或重跑业务；未读资料不写成“产品未说明”，也不从其他厂商或历史需求移植JP公式和通过状态。

## 历史日期资料

[10-05旧版资料](../history/archived-20261005/snapshots/ISOP-2116/design.md) · [旧问题与决定](../history/archived-20261005/snapshots/ISOP-2116/questions.md)。旧规则、问题状态与用例保留为日期快照，不自动作为W26预期；当前问题答复只维护在本单文件。
