# ISOP-2375：VACT 驗證調整设计

[Jira事项](https://alibaba-international.atlassian.net/browse/ISOP-2375) · [问题与决定](questions.md) · [测试用例](test-cases.md) · [采集快照](../reviews/2026-11-27-ISOP-2375.md)

状态：需求整理 / 待确认FAT部署与QA验证；Jira页面状态为`已修復`（缺陷，优先级高，报告人Darren Product Manager，经办人yk），Sprint为`ISOP面板 2026W28 11/26`，关联子任务`ISOP-2386`（QA-VACT 驗證調整，状态`待办`，经办人`ukr`）。本文件依据2026-11-27只读采集形成，不代表已部署FAT、已执行回归或功能已通过。

## 范围与来源

- 依据2026-11-24对FAT及正式站不带token实测与`origin/release`代码排查结果，处理VAPT 003（Employee Email Disclosure）同类敏感字段外泄问题。
- 原报告所列9支API据Jira正文描述已修复；本单补充排查出17项会员端API（15项员工账号/Email/ID及站内信字段，2项会员自身敏感数据）。
- 目标分支为`release`（随本次上版合入），合并后需部署到FAT环境；Jira创建于2026-11-24，最后更新于2026-11-27，页面未见评论、附件或linked work items。

## 变更清单与规则

### 一、回传员工账号名称／Email（优先）

| 序号 | 接口 | 需登录 | 外泄字段 | 代码位置（`origin/release`） | 调整要求 |
| --- | --- | --- | --- | --- | --- |
| 1 | `/promo/list` | 否 | `created_name`、`updated_name`、`created_uid`、`updated_uid` | `promotion model/promo.go:177` `PromoCacheList` | 回传前清空上述4个字段（依赖`omitempty`不输出） |
| 2 | `/promo/task/newbie/daily` | 否 | `created_name`、`updated_name`、`created_uid`、`updated_uid` | `promotion model/task_front.go:373` `NewbieDailyTaskByCache` | `result.Daily = task`赋值前清空`task`的4个字段 |
| 3 | `/promo/task/daily/task` | 否 | `created_name`、`updated_name`、`created_uid`、`updated_uid` | `promotion model/task_daily_front.go:189`、`:239` `DailyTaskByCache` | 两处赋值前均清空4个字段 |
| 4 | `/member/game/list/recommended` | 否 | `updated_name`、`updated_uid` | `member model/game.go:132` `RecommendedGameList`（`Game`位于`model/game.go:96-97`） | 回传前清空，或确认`Game`未用于写缓存后将json tag改为`"-"` |
| 5 | `/member/buriedPoint/detailV2` | 否 | `updated_name`、`updated_uid` | `member model/buried_point.go:28` `BuriedPointDetailV2` | 组装`rets`前清空2个字段 |
| 6 | `/finance/payment/bank/list` | 是 | `created_name`、`updated_name`、`updated_uid` | `finance controller/finance/bank.go:92` `BankList` → `model.PaymentBankList` | 仅在会员端`BankList`拿到结果后清空，不修改与后台共用的model |

### 二、只回传员工 ID（需与第一部分一并处理）

| 序号 | 接口 | 需登录 | 外泄字段 | 代码位置（`origin/release`） | 调整要求 |
| --- | --- | --- | --- | --- | --- |
| 7 | `/member/v2/index`（含filgame、filslots、filplay、karakrus） | 否 | `list`、`nav`的`created_uid`、`updated_uid` | `member model/index.go:294` `filterV2Index` | 在清空名称同一处一并清空ID |
| 8 | `/member/game/listRw` | 否 | `updated_uid` | `member controller/game.go:233` `ListRw` | 回传前清空 |
| 9 | `/member/game/list/recommend` | 是 | `updated_uid` | `member controller/game.go:429` `RecommendList` | 回传前清空（若第4项修改`Game` json tag可一并解决） |
| 10 | `/promo/turntable/detail` | 否 | `operator_uid` | `promotion model/turntable_info.go:1650` | 在清空`OperatorName`同一处一并清空`OperatorUid` |
| 11 | `/promo/task/newbie/list` | 否 | `created_uid`、`updated_uid` | `promotion model/task_front.go:112-113` | 在清空名称同一处一并清空ID |
| 12 | `/promo/task/daily/list` | 否 | `created_uid`、`updated_uid` | `promotion model/task_daily_front.go:90-91` | 在清空名称同一处一并清空ID |
| 13 | `/promo/vip/config` | 是 | `updated_uid` | `promotion model/vip_level.go:123` | 在清空`UpdatedName`同一处一并清空ID |
| 14 | `/member/vip/rule` | 否 | `updated_uid` | `member model/vip.go:49` | 在清空`UpdatedName`同一处一并清空ID |

### 三、站内信列表（上版前必修）

| 序号 | 接口 | 现状与风险 | 调整要求 |
| --- | --- | --- | --- |
| 15 | `/member/message/list` | 正式站（`main`）目前无外泄；`release`与`fat`已改调`MessageListV2`，会回传后台发送者账号`trigger_person`、`maintainer`（`member/model/message.go:279`、`:282`） | 参照`MessagePopupListV2`注释`message.go:153`、`:156`、`:279`、`:282`的这两个字段；并确认会员端是否需要`total_send_count`、`read_count`、`target_users` |

### 四、会员敏感数据（建议一并处理）

| 序号 | 接口 | 外泄字段 | 现状与风险 | 调整要求 |
| --- | --- | --- | --- | --- |
| 16 | `/member/detail` | `member_extra.wallet_password` | 6位数字钱包密码bcrypt哈希可被离线暴力破解；`fat`已在`model/member.go:531`清空（`10cbcd5`），`release`尚未合入 | 将`fat`修正带入`release`并删除`fmt.Println("WalletPassword:", ...)`日志打印；前端沿用`has_wallet_password` |
| 17 | `/member/detail` | `oauth_secrets` | 三方登录授权资料，三个分支均未清空 | 解析完`ThirdPartyTy`、`ThirdPartyName`后，回传前清空`oauth_secrets` |

## 明确验收规则

| 验收点 | 业务预期 | 来源 |
| --- | --- | --- |
| A01 | 不带token调用第1–5、7、8、10–12、14项API（FAT与正式站适用环境），响应中无`created_name`、`updated_name`、`operator_name`、`created_uid`、`updated_uid`、`operator_uid`或为空值 | Jira正文A01 |
| A02 | 带会员token调用第6、9、13项API，响应中无上述员工名称与UID字段或为空值 | Jira正文A02 |
| A03 | 后台发送站内信给测试会员后，会员调用`/member/message/list`，响应中无`trigger_person`、`maintainer`或为空值 | Jira正文A03 |
| A04 | 会员调用`/member/message/popup_list`，维持无`trigger_person`、`maintainer` | Jira正文A04 |
| A05 | 已设钱包密码的会员调用`/member/detail`，`wallet_password`为空、`has_wallet_password`为`true`，且日志无钱包密码哈希 | Jira正文A05 |
| A06 | 三方账号登录会员调用`/member/detail`，`oauth_secrets`为空，三方账号类型（`ThirdPartyTy`）与名称（`ThirdPartyName`）正常显示 | Jira正文A06 |
| A07 | 后台查看活动列表、任务设定、游戏列表、银行列表、埋点设定、转盘活动、站内信，建立人、修改人、操作人照常显示（后台不受影响） | Jira正文A07 |
| A08 | 会员端首页、活动页、签到、任务、VIP、转盘、银行选择、站内信页面显示与操作正常 | Jira正文A08 |

## 待确认及阻塞

- `release`分支合并与FAT实际部署状态、测试环境版本信息（Jira无评论说明）。
- `/member/message/list`的`total_send_count`、`read_count`、`target_users`是否对会员端隐藏（[Q-01](questions.md#q-01)）。
- `/member/game/list/recommended`是否采用修改`Game` json tag方案及对缓存/其他接口的影响（[Q-02](questions.md#q-02)）。
- 第四部分（`wallet_password`、`oauth_secrets`）是否作为本单上版阻塞项，以及日志核验与三方登录测试账号准备情况（[Q-03](questions.md#q-03)、[Q-04](questions.md#q-04)）。
- 原报告9支API是否需纳入本轮一并复测（[Q-05](questions.md#q-05)）。

## 来源与读取范围

| 来源 | 读取结果 |
| --- | --- |
| [Jira ISOP-2375](https://alibaba-international.atlassian.net/browse/ISOP-2375) | 2026-11-27已读取页面正文、字段栏、子任务列表及活动区；状态`已修復`、优先级`高`、Sprint为`ISOP面板 2026W28 11/26`、报告人Darren Product Manager、经办人yk、无附件、无评论、无linked work items。 |
| [子任务 ISOP-2386](https://alibaba-international.atlassian.net/browse/ISOP-2386) | 仅在父单子任务列表读取摘要（`QA-VACT 驗證調整`，状态`待办`，优先级`高`，经办人`ukr`）；未点入子任务详情页或评论。 |

未读取`origin/release`或`fat`代码仓库、服务器日志、子任务详情页；未执行API、后台或会员端UI测试。
