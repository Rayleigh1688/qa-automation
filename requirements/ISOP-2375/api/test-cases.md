# ISOP-2375：原子接口测试用例

[综合测试计划](../test-plan.md) · [验收场景](../test-cases.md) · [需求设计](../design.md) · [待确认事项](../questions.md)

22 条独立用例覆盖 17 条会员端验收路径。每条仅执行一次目标请求，登录、取样和发信在用例前准备。FAT 先行，A01 上版后使用对应正式站入口复核。各用例的发起和判定互不依赖，后台对照和服务日志见综合场景。

## 公共请求与断言

- `{{api_url}}` 取目标环境会员端 `API_URL`，FAT 参考 `https://client-fat.filbet2025.com`。`{{品牌_api_url}}` 指实际品牌请求发往的地址，允许多个品牌共用 origin。其余 `{{...}}` 为本计划的样本参数。
- 客户端 `Lang`、`D` 等非认证请求头跟随对应端。匿名行使用无状态会话并移除 `t/T`、`Authorization`、认证 Cookie 及集合继承认证。会员行使用对应样本会员新会话的 `t`。登录与样本准备不计入原子请求。
- 每行先判 HTTP 200、按契约解码成功、`status === true`、指定业务结构及样本匹配，再从同一响应判断目标字段。检查对象和数组的各级子节点，对契约声明储存结构化 JSON 的字段按结构检查，例如已返回的签到配置。空列表或未命中样本需要补数据核验，不能判通过。
- **员工字段断言（A01／A02）**检查 `created_name`、`updated_name`、`operator_name`、`created_uid`、`updated_uid`、`operator_uid`。每个键须缺失或为字段的空值。默认接受空字符串和 `null`。C23、C26 的 `updated_uid` 也接受整数 `0`，依据见各自用例。站内信人员字段见 C27、C28。
- 证据只保留环境、版本、用例号、HTTP 与业务状态、试验样本命中结果及字段路径和判定。用例中的账号标识只在本机测试输入中使用。
- 请求依据为 [Bruno 固定版本 `a36be1d`](https://git.filbet2025.com/api_doc/backend_api/-/tree/a36be1df02396d905226f4fb035a7c8791028c97/filbet) 和 [现有 P0 接口参数](../../../api/p0/test-cases.csv)。会员详情的业务成功按 TC-001 的 `status`，Bruno 的 `code` 历史示例需在首次 FAT 请求时对照。设计登记状态表示契约准备进度，执行版本见 [Q-03](../questions.md#q-03)。

<!-- case-cards:v1 -->

## 用例总览

| 编号 | 用例名称 | 状态 | 负责人 |
| --- | --- | --- | --- |
| ISOP-2375-C09 | [活动列表隐藏员工字段](#c09) | BLOCKED | 待分派 |
| ISOP-2375-C10 | [新人签到详情隐藏员工字段](#c10) | NOT_RUN | 待分派 |
| ISOP-2375-C11 | [日常签到详情第一处分支隐藏员工字段](#c11) | BLOCKED | 待分派 |
| ISOP-2375-C12 | [日常签到详情第二处分支隐藏员工字段](#c12) | BLOCKED | 待分派 |
| ISOP-2375-C13 | [匿名推荐游戏列表隐藏员工字段](#c13) | NOT_RUN | 待分派 |
| ISOP-2375-C14 | [埋点详情隐藏员工字段](#c14) | NOT_RUN | 待分派 |
| ISOP-2375-C15 | [filgame 首页聚合隐藏员工字段](#c15) | BLOCKED | 待分派 |
| ISOP-2375-C16 | [filslots 首页聚合隐藏员工字段](#c16) | BLOCKED | 待分派 |
| ISOP-2375-C17 | [filplay 首页聚合隐藏员工字段](#c17) | BLOCKED | 待分派 |
| ISOP-2375-C18 | [karakrus 首页聚合隐藏员工字段](#c18) | BLOCKED | 待分派 |
| ISOP-2375-C19 | [组合游戏列表隐藏员工字段](#c19) | NOT_RUN | 待分派 |
| ISOP-2375-C20 | [转盘详情隐藏操作人字段](#c20) | NOT_RUN | 待分派 |
| ISOP-2375-C21 | [新人任务列表隐藏员工字段](#c21) | NOT_RUN | 待分派 |
| ISOP-2375-C22 | [日常任务列表隐藏员工字段](#c22) | NOT_RUN | 待分派 |
| ISOP-2375-C23 | [VIP 规则隐藏员工字段](#c23) | NOT_RUN | 待分派 |
| ISOP-2375-C24 | [会员银行列表隐藏员工字段](#c24) | NOT_RUN | 待分派 |
| ISOP-2375-C25 | [登录后推荐列表隐藏员工字段](#c25) | NOT_RUN | 待分派 |
| ISOP-2375-C26 | [VIP 配置隐藏员工字段](#c26) | NOT_RUN | 待分派 |
| ISOP-2375-C27 | [站内信列表隐藏发送人与维护人](#c27) | NOT_RUN | 待分派 |
| ISOP-2375-C28 | [站内信弹窗维持隐藏后台人员字段](#c28) | NOT_RUN | 待分派 |
| ISOP-2375-C29 | [会员详情隐藏钱包密码字段](#c29) | NOT_RUN | 待分派 |
| ISOP-2375-C30 | [会员详情隐藏三方授权字段](#c30) | NOT_RUN | 待分派 |

## 用例详情

<a id="c09"></a>
### ISOP-2375-C09：活动列表隐藏员工字段

**前置条件：** 已启用的活动，能在后台确认创建或维护记录。

**操作步骤：** 匿名，方法待确认 `{{api_url}}/promo/list`。Jira 给出了路径与匿名条件。方法、查询参数和请求体待从现行客户端请求或后端路由确认。

**预期结果：** 契约确认后绑定成功标识与列表路径，活动列表命中样本。通过员工字段断言，重点核对 `created_name`、`updated_name`、`created_uid`、`updated_uid`。

**待确认：** [Q-06](../questions.md#q-06)

<a id="c10"></a>
### ISOP-2375-C10：新人签到详情隐藏员工字段

**前置条件：** 匿名入口有已启用的新人签到任务，取得该任务 ID。

**操作步骤：** 匿名，GET `{{api_url}}/promo/task/newbie/daily`。无查询参数，无请求体。

**预期结果：** 共同成功断言成立。`data.d` 是对象，`data.d.id` 命中任务。通过员工字段断言，重点核对 `data.d` 下的创建、修改名称和 UID。

**待确认：** 核对样本的任务状态。

<a id="c11"></a>
### ISOP-2375-C11：日常签到详情第一处分支隐藏员工字段

**前置条件：** 使用能触发 Jira 所列 `DailyTaskByCache` 第一处赋值（旧位置 `task_daily_front.go:189`）的任务样本。

**操作步骤：** 匿名，GET `{{api_url}}/promo/task/daily/task`。无查询参数，无请求体。

**预期结果：** 共同成功断言成立。`data.d` 是对象且 `data.d.id` 命中指定任务。取得该分支命中证据后，核对员工字段，重点检查返回任务的创建、修改名称和 UID。

**待确认：** [Q-08](../questions.md#q-08)

<a id="c12"></a>
### ISOP-2375-C12：日常签到详情第二处分支隐藏员工字段

**前置条件：** 使用能触发 Jira 所列 `DailyTaskByCache` 第二处赋值（旧位置 `task_daily_front.go:239`）的任务样本。

**操作步骤：** 匿名，GET `{{api_url}}/promo/task/daily/task`。无查询参数，无请求体。

**预期结果：** 共同成功断言成立。`data.d` 是对象且 `data.d.id` 命中指定任务。取得该分支命中证据后，核对员工字段，重点检查返回任务的创建、修改名称和 UID。

**待确认：** [Q-08](../questions.md#q-08)

<a id="c13"></a>
### ISOP-2375-C13：匿名推荐游戏列表隐藏员工字段

**前置条件：** 第一页配置有可见推荐游戏，取得用于对照的游戏 ID。

**操作步骤：** 匿名，GET `{{api_url}}/member/game/list/recommended`。`page=1`、`page_size=10`，无请求体。

**预期结果：** 共同成功断言成立。`data.d` 是非空数组，目标 `game_id` 存在，分页 `data.t`、`data.s` 保留。通过员工字段断言，重点核对游戏记录的 `updated_name`、`updated_uid`。

**待确认：** [Q-02](../questions.md#q-02)

<a id="c14"></a>
### ISOP-2375-C14：埋点详情隐藏员工字段

**前置条件：** 取得 FAT 当前启用且可见的广告 ID。

**操作步骤：** 匿名，GET `{{api_url}}/member/buriedPoint/detailV2`。`ad_id={{ad_id}}`，无请求体。

**预期结果：** 共同成功断言成立。CBOR 可解码，`data` 是非空数组且命中 `ad_id`。通过员工字段断言，重点核对各埋点对象的 `updated_name`、`updated_uid`。

**待确认：** 核对各环境当前启用的广告 ID。

<a id="c15"></a>
### ISOP-2375-C15：filgame 首页聚合隐藏员工字段

**前置条件：** 取得 filgame 当前首页的匿名请求入口、客户端请求头以及可识别的首页和导航样本。

**操作步骤：** 匿名，GET `{{filgame_api_url}}/member/v2/index`。现有基础版无查询参数、无请求体。品牌入口、请求头和可能的路由参数按该品牌真实请求补齐。

**预期结果：** 共同成功断言成立。`data.list`、`data.nav` 各命中该品牌的样本。通过员工字段断言，重点覆盖两处数组的 `created_uid`、`updated_uid`，同时确认首页业务数据保留。

**待确认：** [Q-07](../questions.md#q-07)

<a id="c16"></a>
### ISOP-2375-C16：filslots 首页聚合隐藏员工字段

**前置条件：** 取得 filslots 当前首页的匿名请求入口、客户端请求头以及可识别的首页和导航样本。

**操作步骤：** 匿名，GET `{{filslots_api_url}}/member/v2/index`。现有基础版无查询参数、无请求体。品牌入口、请求头和可能的路由参数按该品牌真实请求补齐。

**预期结果：** 共同成功断言成立。`data.list`、`data.nav` 各命中该品牌的样本。通过员工字段断言，重点覆盖两处数组的 `created_uid`、`updated_uid`，同时确认首页业务数据保留。

**待确认：** [Q-07](../questions.md#q-07)

<a id="c17"></a>
### ISOP-2375-C17：filplay 首页聚合隐藏员工字段

**前置条件：** 取得 filplay 当前首页的匿名请求入口、客户端请求头以及可识别的首页和导航样本。

**操作步骤：** 匿名，GET `{{filplay_api_url}}/member/v2/index`。现有基础版无查询参数、无请求体。品牌入口、请求头和可能的路由参数按该品牌真实请求补齐。

**预期结果：** 共同成功断言成立。`data.list`、`data.nav` 各命中该品牌的样本。通过员工字段断言，重点覆盖两处数组的 `created_uid`、`updated_uid`，同时确认首页业务数据保留。

**待确认：** [Q-07](../questions.md#q-07)

<a id="c18"></a>
### ISOP-2375-C18：karakrus 首页聚合隐藏员工字段

**前置条件：** 取得 karakrus 当前首页的匿名请求入口、客户端请求头以及可识别的首页和导航样本。

**操作步骤：** 匿名，GET `{{karakrus_api_url}}/member/v2/index`。现有基础版无查询参数、无请求体。品牌入口、请求头和可能的路由参数按该品牌真实请求补齐。

**预期结果：** 共同成功断言成立。`data.list`、`data.nav` 各命中该品牌的样本。通过员工字段断言，重点覆盖两处数组的 `created_uid`、`updated_uid`，同时确认首页业务数据保留。

**待确认：** [Q-07](../questions.md#q-07)

<a id="c19"></a>
### ISOP-2375-C19：组合游戏列表隐藏员工字段

**前置条件：** 选取 `op` 场馆内可返回的游戏样本，或替换为已配置且有数据的场馆。

**操作步骤：** 匿名，GET `{{api_url}}/member/game/listRw`。`page=1`、`page_size=10`、`venues=op`、`sort=4`，无请求体。

**预期结果：** 共同成功断言成立。`data.d` 是非空数组，目标 `game_id` 存在，`data.t`、`data.s` 保留。通过员工字段断言，重点核对每条记录的 `updated_uid`。

**待确认：** 沿用现有 TC-012 参数，执行前核对场馆样本。

<a id="c20"></a>
### ISOP-2375-C20：转盘详情隐藏操作人字段

**前置条件：** 取得当前已启用的转盘活动 `pid` 及其奖项配置。

**操作步骤：** 匿名，GET `{{api_url}}/promo/turntable/detail`。`pid={{turntable_pid}}`，无请求体。Bruno 的 `16` 仅作请求示例。

**预期结果：** 共同成功断言成立。`data` 是对象，奖项列表命中该活动已配置的奖项。通过员工字段断言，重点核对 `operator_name`、`operator_uid`。

**待确认：** 核对当前环境的活动 ID。

<a id="c21"></a>
### ISOP-2375-C21：新人任务列表隐藏员工字段

**前置条件：** 存在返回给匿名用户的新人任务，取得目标任务 ID。

**操作步骤：** 匿名，GET `{{api_url}}/promo/task/newbie/list`。无查询参数，无请求体。

**预期结果：** 共同成功断言成立。`data.d` 是非空数组，命中样本 `id`。通过员工字段断言，重点核对每条任务的 `created_uid`、`updated_uid`。

**待确认：** 核对当前任务样本。

<a id="c22"></a>
### ISOP-2375-C22：日常任务列表隐藏员工字段

**前置条件：** 存在返回给匿名用户的日常任务，取得目标任务 ID。

**操作步骤：** 匿名，GET `{{api_url}}/promo/task/daily/list`。无查询参数，无请求体。

**预期结果：** 共同成功断言成立。`data.d` 是非空数组，命中样本 `id`。通过员工字段断言，重点核对每条任务的 `created_uid`、`updated_uid`。

**待确认：** 核对当前任务样本。

<a id="c23"></a>
### ISOP-2375-C23：VIP 规则隐藏员工字段

**前置条件：** 存在匿名可见的 VIP 规则，确定一个目标等级和已配置规则。

**操作步骤：** 匿名，GET `{{api_url}}/member/vip/rule`。无查询参数，无请求体。

**预期结果：** 共同成功断言成立。`data` 是规则映射，目标等级下有有效规则。通过员工字段断言。按 2026-11-27 FAT 定向复核，`updated_uid` 也可返回整数 `0`。

**待确认：** 核对等级样本，确认整数零的正式接口契约。

<a id="c24"></a>
### ISOP-2375-C24：会员银行列表隐藏员工字段

**前置条件：** 使用普通测试会员，取得启用银行的 ID、代码及其所在页。后台保留同一银行的操作人信息供对照。

**操作步骤：** 会员会话，GET `{{api_url}}/finance/payment/bank/list`。`page={{bank_page}}`、`page_size=10`，无请求体。现有 TC-023 用第 2 页。

**预期结果：** 共同成功断言成立。`data.d` 是数组，命中目标银行 `id`、`code`，`name` 和 `data.t`、`data.s` 保留。通过员工字段断言，重点核对 `created_name`、`updated_name`、`updated_uid`。

**待确认：** 核对样本所在页。

<a id="c25"></a>
### ISOP-2375-C25：登录后推荐列表隐藏员工字段

**前置条件：** 使用普通测试会员，推荐配置存在可见游戏。

**操作步骤：** 会员会话，GET `{{api_url}}/member/game/list/recommend`。无查询参数，无请求体。沿用 TC-013。

**预期结果：** 共同成功断言成立。`data.d` 非空且包含指定游戏，`data.t`、`data.s` 保留。通过员工字段断言，重点核对每条游戏的 `updated_uid`。

**待确认：** [Q-02](../questions.md#q-02)

<a id="c26"></a>
### ISOP-2375-C26：VIP 配置隐藏员工字段

**前置条件：** 使用普通测试会员，并准备已有配置的 VIP 等级。

**操作步骤：** 会员会话，GET `{{api_url}}/promo/vip/config`。无查询参数，无请求体。

**预期结果：** 共同成功断言成立。`data` 是对象，包含指定等级配置及其 `level`、`ty`。通过员工字段断言。接口文档规定已废弃的 `updated_uid` 返回整数 `0`，本用例将其判为空值。 [FB 文档更新](https://git.filbet2025.com/api_doc/backend_api/-/commit/c2a1dc2aa00462ce74086f404ae5592649f0fb38)

**待确认：** 核对目标等级及配置。

<a id="c27"></a>
### ISOP-2375-C27：站内信列表隐藏发送人与维护人

**前置条件：** 目标测试会员已有一条可读站内信，准备其消息 ID、标题、正文及所在页。

**操作步骤：** 会员会话，GET `{{api_url}}/member/message/list`。`page={{message_page}}`、`page_size=10`，无请求体。优先使用第 1 页。

**预期结果：** 共同成功断言成立。`data.d` 是非空数组，命中目标消息且标题、正文与样本一致。整个响应的 `trigger_person`、`maintainer` 缺失或为契约空值。

**待确认：** [Q-01](../questions.md#q-01) 仅影响额外统计和目标字段。

<a id="c28"></a>
### ISOP-2375-C28：站内信弹窗维持隐藏后台人员字段

**前置条件：** 目标测试会员已有符合弹窗条件的可读站内信，准备消息 ID、标题及正文。

**操作步骤：** 会员会话，GET `{{api_url}}/member/message/popup_list`。无查询参数，无请求体。

**预期结果：** 共同成功断言成立。`data` 是非空数组，命中目标弹窗消息且标题、正文与样本一致。整个响应的 `trigger_person`、`maintainer` 缺失、为 `null` 或为空字符串。

**待确认：** 确认弹窗有效期和可见条件。

<a id="c29"></a>
### ISOP-2375-C29：会员详情隐藏钱包密码字段

**前置条件：** 使用已设置钱包密码的专用测试会员，取得其 UID。

**操作步骤：** 会员会话，GET `{{api_url}}/member/detail`。无查询参数，无请求体。沿用 TC-001 的请求及成功契约。

**预期结果：** 共同成功断言成立。`data.uid` 匹配，`data.member_extra` 是对象，`data.has_wallet_password` 严格为布尔 `true`，`data.member_extra.wallet_password` 缺失或为契约空值。

**待确认：** [Q-04](../questions.md#q-04)。服务日志按 [C05](../test-cases.md#c05) 验收。

<a id="c30"></a>
### ISOP-2375-C30：会员详情隐藏三方授权字段

**前置条件：** 通过三方登录的专用测试会员，取得其 UID 及预期三方账号类型和展示名称。

**操作步骤：** 会员会话，GET `{{api_url}}/member/detail`。无查询参数，无请求体。沿用 TC-001 的请求及成功契约。

**预期结果：** 共同成功断言成立。`data.uid` 匹配，`data.oauth_secrets` 缺失或为契约空值，`data.third_party_ty`、`data.third_party_name` 与该三方账号的预期展示一致。

**待确认：** [Q-04](../questions.md#q-04)

## 验收关联与检查方式

| 编号 | 优先级/验收点 | 方式 |
| --- | --- | --- |
| ISOP-2375-C09 | 高 / A01 | API |
| ISOP-2375-C10 | 高 / A01 | API |
| ISOP-2375-C11 | 高 / A01 | API |
| ISOP-2375-C12 | 高 / A01 | API |
| ISOP-2375-C13 | 高 / A01 | API |
| ISOP-2375-C14 | 高 / A01 | API |
| ISOP-2375-C15 | 高 / A01 | API |
| ISOP-2375-C16 | 高 / A01 | API |
| ISOP-2375-C17 | 高 / A01 | API |
| ISOP-2375-C18 | 高 / A01 | API |
| ISOP-2375-C19 | 高 / A01 | API |
| ISOP-2375-C20 | 高 / A01 | API |
| ISOP-2375-C21 | 高 / A01 | API |
| ISOP-2375-C22 | 高 / A01 | API |
| ISOP-2375-C23 | 高 / A01 | API |
| ISOP-2375-C24 | 高 / A02 | API |
| ISOP-2375-C25 | 高 / A02 | API |
| ISOP-2375-C26 | 高 / A02 | API |
| ISOP-2375-C27 | 高 / A03 | API |
| ISOP-2375-C28 | 高 / A04 | API |
| ISOP-2375-C29 | 高 / A05 | API |
| ISOP-2375-C30 | 高 / A06 | API |

<!-- /case-cards -->
