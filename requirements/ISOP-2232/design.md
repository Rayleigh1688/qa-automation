# ISOP-2232：PT免费旋转串接设计

[设计](design.md) · [问题与决定](questions.md) · [测试重点](test-cases.md) · [W27扫描](../reviews/2026W27-20261016.md)

2026-10-16初扫：本单要求接入PT的FREESPIN1，按预建模板派发次数，赢额即时进入钱包并由本平台计算流水。Jira、Confluence、PT接口文档及派发原型已读，尚未验证业务实现。主要待核实项是实际模板的奖金模式、重复派发限制、旧自动派发切换，以及异步发放／回调／同步的一致性。

## 明确规则

| 验收编号 | 规则 | 来源定位 |
| --- | --- | --- |
| AC-01 | 手动、批量派发支持PT；选择PT后模板代码必填且最多32字符，次数必填；取消PT或切换层级后隐藏并清空模板值 | Jira 表单、A01—A05 |
| AC-02 | 单次投注额由PT模板决定；后台单次投注额、最低／最高提款对PT不生效，并显示说明；平台流水倍数、场馆限制、有效期等沿既有规则 | Jira 表单、A06—A08 |
| AC-03 | PROVIDER使用模板游戏；GAME传入所选PT游戏；发放调用`giveFreeSpins`，不传`amount`／`betValues` | Jira 串接§派发、B01—B06；Confluence §2.i |
| AC-04 | 本平台派发ID作为`remoteBonusCode`，保存PT返回的`bonusInstanceCode`；厂商事件ID展示后者；PT错误代码及消息应可见 | Jira 派发、列表／详情 |
| AC-05 | PT免费旋转`bet.amount=0`，不扣钱包；解析`bonusChanges[].remoteBonusCode`及`freeSpinChange`更新次数、识别FS并排除有效投注；首笔回调提供实际单次投注额 | Jira 回调、C01、C02、C05；Confluence §6.i |
| AC-06 | 游戏结果的`pay.amount`按PT回调入钱包，以`bonusInstanceCode`关联派发累计赢额；赢额乘平台流水倍数生成流水并保留场馆限制；不另走PT `transferFunds` | Jira 回调、C03、C04；Confluence §5.i |
| AC-07 | active查询用剩余次数更新进度；active消失后查history及`removalReason`判断完成／过期／作废，不能仅凭消失判完成 | Jira 同步／状态映射；Confluence §3.i |
| AC-08 | 后台只允许“已领取”执行作废，调用PT `removeBonus`；成功才变更状态，失败保留原状态并展示错误 | Jira 作废、D01—D04 |
| AC-09 | 批量发放逐玩家异步处理；进入游戏不额外携带FS参数 | Jira 批量／游戏启动；Confluence §4.i |

## 接口合同核对

PT文档当前页面标记为1.0.63（2026-09-11），以下为文档合同，不是已测结果。

| 核对点 | 已读合同与处理 |
| --- | --- |
| 派发身份和时间 | `username`须与启动游戏一致并含kiosk前缀；`remoteBonusCode`为本平台关联码，`remoteBonusDate`及`expirationDate`使用GMT毫秒格式。`playerData`需与PHP／PH模板准备一致 |
| 回调路径 | 官方文档路径为`/gameRoundResult`；Jira示例写`/gameroundresult`。实施时核实际服务路由，不直接复制大小写差异 |
| 钱包金额 | `pay.amount`已包含`bonusWinningsInfo`中的奖金信息；后者用于归属和分项，不能再加一次。单局可有多次结果回调，不能仅按局号去重 |
| 回调重试 | PT会重试Bet、GameRoundResult，合同要求幂等；HTTP200仍需读取业务成功／错误体。次数、钱包和流水都应防重复，具体事件键和提交边界见Q-08 |
| 过期token | PT合同允许已处理Bet重试和GameRoundResult继续返回既有／结算结果；不能统一按登录过期丢弃结算回调 |
| 同步范围 | history只覆盖最近一年，最多返回500条。找不到记录不等于未发放或已完成；需可关联的本地记录及异常处理 |
| 状态枚举 | 官方`removalReason`多于Jira映射，且已使用完毕是否立即进入history仍由Jira列为待确认；不能把所有移除原因都映射为完成 |

## 来源差异与影响

Jira与Confluence v17均明确即时入钱包；PT文档的Spend-only说明也支持该模式，但“Bonus Scenario: FreeSpin”的示例又包含内部奖金、PT流水及后续转账。必须确认实际FREESPIN1模板采用哪个模型，不能把另一模式的示例搬入本单结算。PT FAQ还写同一玩家可分配多个相同模板ID，但只能接受第一个；需要明确约束范围后才能设计重复活动与补发。

Confluence通用批量流程说明先建立本地派发记录、不直接请求第三方，本单要求逐玩家异步派发，两者可以通过队列衔接，但触发时点、未知结果重试和失败状态仍需工程合同。Jira明确现有进游戏自动发放使用`venue:freespin:playtech:{uid}`及`freespin:config:playtech`，是否停用尚未决定；新旧入口并存可能重复派发。

详细问题只维护在[问题与决定](questions.md)，不将疑点直接登记成产品缺陷。

## 来源与读取范围

| 来源 | 来源版本／时间 | 2026-10-16读取范围 |
| --- | --- | --- |
| [Jira ISOP-2232](https://alibaba-international.atlassian.net/browse/ISOP-2232) | 更新于2026-10-16 14:08:10.301（UTC+8） | 正文全读，评论0条、remoteLinks空；2252—2254三子任务正文／评论均空，均为待办 |
| [FreeSpin串接](https://alibaba-international.atlassian.net/wiki/spaces/bZaHTt6TIllW/pages/351535119) | v17，2026-10-13 09:48:56.430（UTC）；版本备注`PT: FREESPIN1 only` | 正文全读，重点§1及各节i.PT；页脚和行内评论均为空 |
| [PT单一钱包API](https://doc.crossits.com/playtech/seamless/cn.html#api-giveFreeSpins) | 1.0.63（2026-09-11） | 已读giveFreeSpins、active／history、bet／gameRoundResult、removeBonus、奖金模型、重试及FAQ相关合同；未调用任何厂商接口 |
| [派发原型](https://vip-admin-gray.vercel.app/admin/freespin-grants) | 页面未标版本 | 已读列表及手动派发表单、PROVIDER选择PT后的模板和限制提示；未提交、未同步／作废，批量完整交互及详情未逐项操作 |

主单为待办，所属Sprint215为`ISOP面板 2026W27 10/29`、future、无起止日期。原型样本数值与状态不作真实证据。未刷新本仓库正式服务接口或实现、未创建CSV／执行计划，业务执行均未开始。
