# ISOP-2393 每日投注上限接口测试设计

[Jira 需求](https://alibaba-international.atlassian.net/browse/ISOP-2393) · [接口契约评审](api/contract-review.md) · [问题与决定](questions.md) · [功能用例](test-cases.md) · [接口测试草案](api/test-plan.md) · [早期 Jira 采集快照](../reviews/2026-11-27-ISOP-2393.md)

2026-11-27 已对照 Jira 和 FB 接口文档。截图四笔提交覆盖 3 个 HTTP 方法与路径组合，后台设置和取消共用同一个 POST。另有同日较早提交的会员保存接口。当前文档覆盖配置的查询与写入，游戏入口拦截、后台取消参数、部分字段类型及日志契约待补。FAT 部署和业务行为仍待验证。

## 范围与来源

- Filbet、Filplay 的 App/H5 在 `Responsible Gaming` 将 `Daily loss limit` 替换为每日投注上限。后台涉及会员详情的功能限制和角色配置。
- 两站独立保存、独立计算，业务日按 GMT+8 自然日切换。对于旧 `Daily loss limit` 存量数据，见[迁移与兼容待确认项](questions.md#q-02)。

## 明确规则

| 验收点 | 业务预期 | 来源 |
| --- | --- | --- |
| AC-01 | Filbet、Filplay两站各自设定与计算每日投注上限；一天按`00:00～23:59 (GMT+8)`计算。 | Jira正文§說明 |
| AC-02 | 会员未设定上限时，可在App/H5设定每日投注上限（PHP，需大于0，不设最小值、最大值）；送出前需二次确认并提示确认后当日无法修改或取消，确认后立即生效。 | Jira正文§1 |
| AC-03 | 会员当天设定或调整后，当日不可再修改或取消，API 同样校验。次日可调高、调低或取消，调整立即生效并再次锁定。取消后状态关闭、上限清空；同日重设时机见 [Q-11](questions.md#q-11)。 | Jira正文§1 |
| AC-04 | 当日锁定仅依会员自身设定或调整判断，不受后台调整影响：会员当日未自行设定/调整过，后台调整后会员仍可自行调整；会员当日已自行设定/调整过，后台调整后仍维持锁定。 | Jira正文§1 |
| AC-05 | 当日投注额采用「会员日统计」的投注额（不含Free Spin），依日统计更新时间计算（非实时）；进入游戏时若当日投注额`>=`每日上限，阻挡进入游戏并提示`You have reached your daily betting limit. Please try again tomorrow.`；已在游戏中不中断（当日投注额可超过上限）；次日00:00起重新计算。 | Jira正文§2 |
| AC-06 | 后台`会员详情 > 功能限制`的「功能限制总览」上方显示「每日投注上限」区块：状态（开启／关闭）、每日上限（`₱`，关闭显示 `-`）、设定来源（会员／后台）、最后设定时间（`YYYY-MM-DD HH:mm:ss`）、`ⓘ`提示及「变更记录」按钮；开启时显示「取消」，任何状态可显示「修改」，写入按钮依编辑权限控制。 | Jira正文§3 |
| AC-07 | 后台「修改」弹窗：每日上限必填、大于0、小数两位（未填提示`請輸入每日上限`），修改时带入当前金额；原因必填、最多200字（未填提示`請輸入原因`）。「取消上限」原因必填，确认后状态关闭、上限清空。保存后立即生效并写入变更记录。 | Jira正文§3 |
| AC-08 | 后台「变更记录」弹窗在任何状态均可开启，字段为时间、来源（会员／后台）、操作人（会员账号或后台账号）、操作（修改／取消）、修改前、修改后、原因（会员操作显示 `-`）；取消后金额显示 `-`；记录会员与后台所有变更，按时间由新到旧排序，每页10笔。 | Jira正文§3 |
| AC-09 | `系统管理 > 角色配置`新增独立权限「每日投注上限－编辑」（默认不勾选）；有权限显示「修改」及开启态的「取消」，无权限仅可查看区块与变更记录、不显示编辑按钮，且API校验权限并拒绝无权限操作。 | Jira正文§3 權限 |

## 接口能力预期与当前评估

| 能力 | 文档评估 | 测试草案 |
| --- | --- | --- |
| 会员查询上限、当日投注额和剩余锁定时间 | 会员详情有对应字段，字段类型须按最新示例及实测确认。 | A01、A07 |
| 后台查询指定会员的状态和变更记录 | 复用原限制状态接口，金额类型、设置来源及分页契约待补。 | A02、A06 |
| 会员设置、修改、取消及当日一次锁定 | 有会员保存文档，需验证锁定、取消和跨日读回。 | A03、A07、A10 |
| 后台修改、取消、独立权限及审计 | 两个请求模板共用一个写路径，取消枚举与请求编码待确认。 | A04—A06、A10 |
| 新进游戏拦截和两站隔离 | 需双方环境、入口契约、可追溯统计样本；不能从详情返回推断拦截。 | A08、A09 |

## 子任务 ISOP-2398（FilPlay H5）规格补充

来源：[ISOP-2398](https://alibaba-international.atlassian.net/browse/ISOP-2398)（`[FilPlay] 客戶端 H5 - 新增每日投注限制`，经办人`FE Gongben`，报告人`Axing Product Manager`，状态`待办`，被`ISOP-2399`克隆）。依据PAGCOR于2026-11-26检查后的合规要求，预期上线时间为`2026-12-01 前`。Figma设计稿：[260428_FilPlay_Redesign (node-id=4788-15064)](https://www.figma.com/design/5Y2Qpf6qxGWBwAIwkkqxDY/260428_FilPlay_Redesign?node-id=4788-15064&t=gnUu2VZGQ2coHafO-0)。

| 阶段/场景 | 子任务规则与文案 | 对应父单/待确认 |
| --- | --- | --- |
| 设置Daily Betting Limit | 原`Daily Loss Limit`标题改为`Daily Betting Limit`；输入数值点击保存后展示二次确认弹窗，文案：`After setting a Daily Betting Limit, you cannot remove it until tomorrow.`；点击确认后生效 | AC-02 |
| 生效期间展示 | 展示`Limit`（设置的投注额度）、`Time remaining`（当前自然日结束倒计时）、`Remove`按钮（设定当日不可点击）及提示：`You can remove this limit from 12:00 AM 11/27/2026. The limit remains active until removal is complete.`（次日`Remove`恢复可点击后该提示消失） | AC-02、AC-03 |
| 生效且被触发 | 投注额达到设定值后，在`Limit`数值后展示`Limit Reached`标签；点击进入游戏拦截并弹出限制弹窗，文案：`You have reached your daily betting limit.`；弹窗内点击`OK`隐藏弹窗，点击`View Settings`跳转到`Responsible Gaming`设置页 | AC-05；文案差异见[Q-07](questions.md#q-07) |
| 次日移除设置 | 到下一个自然日后`Remove`按钮恢复可点击，点击后直接移除`Daily Betting Limit`设置，移除后投注不受限制 | AC-03；交互差异见[Q-08](questions.md#q-08) |

## 来源与适用范围

2026-11-27 读取 [ISOP-2393 父单](https://alibaba-international.atlassian.net/browse/ISOP-2393)（更新于 17:10 UTC+8，待办）、[H5 ISOP-2398](https://alibaba-international.atlassian.net/browse/ISOP-2398)（待办）、[App ISOP-2399](https://alibaba-international.atlassian.net/browse/ISOP-2399)（FAT 测试）、[后台 ISOP-2400](https://alibaba-international.atlassian.net/browse/ISOP-2400)（进行中）、[后端 ISOP-2401](https://alibaba-international.atlassian.net/browse/ISOP-2401)（待办，正文为空）。五单返回的评论列表均为空。父单未返回远程链接，正文未见 Lark 链接；视觉附件只核对清单，Figma 与后台原型未审阅。

接口业务断言采用父单 §1—3。后台子单沿用较早的「已设置／未设置」和独立「设置」动作描述；App/H5 子单侧重 Remove 和弹窗。游戏拦截文案和次日操作分别见 [Q-07](questions.md#q-07)、[Q-08](questions.md#q-08)。App 子单处于 FAT 测试，两站客户端与后端部署仍待核实，见 [Q-13](questions.md#q-13)。
