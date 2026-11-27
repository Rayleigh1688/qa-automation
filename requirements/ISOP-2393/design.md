# ISOP-2393：每日投注限制功能设计

[Jira事项](https://alibaba-international.atlassian.net/browse/ISOP-2393) · [问题与决定](questions.md) · [测试用例](test-cases.md) · [采集快照](../reviews/2026-11-27-ISOP-2393.md)

状态：需求评审 / 已补充子任务`ISOP-2398`（FilPlay H5）；Jira父单状态为`待办`（故事，优先级高，报告人Darren Product Manager，经办人未分配），关联子任务为`ISOP-2398`（FilPlay H5，FE Gongben，`待办`，报告人Axing Product Manager，目标`2026-12-01 前`）与`ISOP-2399`（FilPlay App，safi，`待办`）。本文件依据2026-11-27只读采集形成，不代表提测、部署或功能已通过。

## 范围与来源

- 范围覆盖Filbet、Filplay用户端（App、H5）的`Responsible Gaming`页面及管理后台`会员管理 > 会员列表 > 会员详情 > 功能限制`与`系统管理 > 角色配置`。
- 将用户端`Responsible Gaming`页原`Daily loss limit`改为每日投注上限；Filbet、Filplay两站各自设定、各自计算，每日周期为`00:00～23:59 (GMT+8)`。
- Jira正文包含原型链接（`https://vip-admin-gray.vercel.app/admin/members/U10033`）及3张附件截图（`isop2393-restriction-tab_annotated.png`、`isop2393-edit-modal.png`、`isop2393-log-modal_cropped.png`）；本轮未打开原型或下载附件。

## 明确规则

| 验收点 | 业务预期 | 来源 |
| --- | --- | --- |
| AC-01 | Filbet、Filplay两站各自设定与计算每日投注上限；一天按`00:00～23:59 (GMT+8)`计算。 | Jira正文§說明 |
| AC-02 | 会员未设定上限时，可在App/H5设定每日投注上限（PHP，需大于0，不设最小值、最大值）；送出前需二次确认并提示确认后当日无法修改或取消，确认后立即生效。 | Jira正文§1 |
| AC-03 | 会员当日完成设定或调整后，当日不可再修改或取消（API同样校验当日锁定）；次日起可调高、调低或取消，调整后立即生效并再次当日锁定。 | Jira正文§1 |
| AC-04 | 当日锁定仅依会员自身设定或调整判断，不受后台调整影响：会员当日未自行设定/调整过，后台调整后会员仍可自行调整；会员当日已自行设定/调整过，后台调整后仍维持锁定。 | Jira正文§1 |
| AC-05 | 当日投注额采用「会员日统计」的投注额（不含Free Spin），依日统计更新时间计算（非实时）；进入游戏时若当日投注额`>=`每日上限，阻挡进入游戏并提示`You have reached your daily betting limit. Please try again tomorrow.`；已在游戏中不中断（当日投注额可超过上限）；次日00:00起重新计算。 | Jira正文§2 |
| AC-06 | 后台`会员详情 > 功能限制`的「功能限制总览」上方显示「每日投注上限」区块：状态（未设定／已设定）、每日上限（`₱`，未设定显示`-`）、设定来源（会员／后台）、最后设定时间（`YYYY-MM-DD HH:mm:ss`）、`ⓘ`提示及「变更记录」按钮；已设定显示「修改」「取消上限」，未设定显示「设定」。 | Jira正文§3 |
| AC-07 | 后台「设定／修改」弹窗：每日上限必填、大于0、小数两位（未填提示`請輸入每日上限`），修改时带入当前金额；原因必填、最多200字（未填提示`請輸入原因`）。「取消上限」原因必填，确认后状态为未设定。保存后立即生效并写入变更记录。 | Jira正文§3 |
| AC-08 | 后台「变更记录」弹窗在任何状态均可开启，字段为时间、来源（会员／后台）、操作人（会员账号或后台账号）、操作（设定／修改／取消）、修改前、修改后、原因（会员操作显示`-`）；记录会员与后台所有变更，按时间由新到旧排序，每页10笔。 | Jira正文§3 |
| AC-09 | `系统管理 > 角色配置`新增独立权限「每日投注上限－编辑」（默认不勾选）；有权限显示「设定」「修改」「取消上限」，无权限仅可查看区块与变更记录、不显示编辑按钮，且API校验权限并拒绝无权限操作。 | Jira正文§3 權限 |

## 待确认及阻塞

- 会员端输入小数位限制、非法输入提示与`Responsible Gaming`页面替换后的具体文案/设计稿（[Q-01](questions.md#q-01)）。
- 存量已设定`Daily loss limit`会员数据的迁移或兼容规则（[Q-02](questions.md#q-02)）。
- 进游戏阻挡涵盖的启动入口与API边界（[Q-03](questions.md#q-03)）。
- 取消上限弹窗的校验与提示细节（[Q-04](questions.md#q-04)）。
- Filbet客户端及后端/后台任务单与排期归属（[Q-05](questions.md#q-05)）。
- 原型链接与附件截图（含`ISOP-2398` Figma与7张截图）的细节核对（[Q-06](questions.md#q-06)）。
- 父单与`ISOP-2398`进游戏阻挡弹窗文案差异（[Q-07](questions.md#q-07)）及次日调整／直接移除交互差异（[Q-08](questions.md#q-08)）。

未取得相应答复前，依赖项相关用例保持`BLOCKED`或`NOT_RUN`，不从现有`Daily loss limit`实现反推新需求口径。

## 子任务 ISOP-2398（FilPlay H5）规格补充

来源：[ISOP-2398](https://alibaba-international.atlassian.net/browse/ISOP-2398)（`[FilPlay] 客戶端 H5 - 新增每日投注限制`，经办人`FE Gongben`，报告人`Axing Product Manager`，状态`待办`，被`ISOP-2399`克隆）。依据PAGCOR于2026-11-26检查后的合规要求，预期上线时间为`2026-12-01 前`。Figma设计稿：[260428_FilPlay_Redesign (node-id=4788-15064)](https://www.figma.com/design/5Y2Qpf6qxGWBwAIwkkqxDY/260428_FilPlay_Redesign?node-id=4788-15064&t=gnUu2VZGQ2coHafO-0)。

| 阶段/场景 | 子任务规则与文案 | 对应父单/待确认 |
| --- | --- | --- |
| 设置Daily Betting Limit | 原`Daily Loss Limit`标题改为`Daily Betting Limit`；输入数值点击保存后展示二次确认弹窗，文案：`After setting a Daily Betting Limit, you cannot remove it until tomorrow.`；点击确认后生效 | AC-02 |
| 生效期间展示 | 展示`Limit`（设置的投注额度）、`Time remaining`（当前自然日结束倒计时）、`Remove`按钮（设定当日不可点击）及提示：`You can remove this limit from 12:00 AM 11/27/2026. The limit remains active until removal is complete.`（次日`Remove`恢复可点击后该提示消失） | AC-02、AC-03 |
| 生效且被触发 | 投注额达到设定值后，在`Limit`数值后展示`Limit Reached`标签；点击进入游戏拦截并弹出限制弹窗，文案：`You have reached your daily betting limit.`；弹窗内点击`OK`隐藏弹窗，点击`View Settings`跳转到`Responsible Gaming`设置页 | AC-05；文案差异见[Q-07](questions.md#q-07) |
| 次日移除设置 | 到下一个自然日后`Remove`按钮恢复可点击，点击后直接移除`Daily Betting Limit`设置，移除后投注不受限制 | AC-03；交互差异见[Q-08](questions.md#q-08) |

## 来源与读取范围

| 来源 | 读取结果 |
| --- | --- |
| [Jira ISOP-2393](https://alibaba-international.atlassian.net/browse/ISOP-2393) | 2026-11-27已读取页面正文、字段栏、附件清单、子任务列表及活动区；状态`待办`、优先级`高`、报告人Darren Product Manager、经办人未分配、无Sprint、无评论、无linked work items。 |
| [Jira ISOP-2398](https://alibaba-international.atlassian.net/browse/ISOP-2398) | 2026-11-27已读取子任务正文、字段栏、7张截图附件清单（`image-20261127-061352.png`等）、Figma链接及`is cloned by ISOP-2399`关联；无评论，未下载附件或打开Figma。 |
| 附件与原型 | 已读取父单3张截图与原型URL、`ISOP-2398` 7张截图与Figma URL；本轮均未下载附件或打开原型/Figma页面。 |
| 其他子任务 | 仅在列表读取`ISOP-2399`（FilPlay App，safi，`待办`）摘要；未点入`ISOP-2399`详情页。 |

未读取原型页面、Figma设计稿、附件图像内容、`ISOP-2399`详情页或代码仓；未执行API、后台或客户端测试。
