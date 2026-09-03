# FAT 管理后台“页面 → 操作 → 接口”扫描

## 当前结论

本目录是本轮 FAT 管理后台扫描的独立工作区。它不修改 `AI-HANDOFF.md`、现有 P0/P1 用例、`api/inventory/interfaces.csv` 或 `api/catalog/`。

2026-09-03 已完成：

- 执行前检查 Git 状态并保留已有未跟踪目录；
- 完整阅读仓库入口、API/UI 方法、FAT 环境、后台 API、inventory 和 catalog 规则；
- FAT 后台两步 API 登录成功；
- 现有后台只读探针 13/13 通过，加上两步登录共 15 个成功请求；
- 通过 `GET /admin/priv/list` 递归建立 12 个一级菜单、68 个二级页面/权限入口及 253 个下级操作；
- 下载并校验 FAT 当前前端 bundle，静态提取 60 条 UI 路由和 483 条 `/admin/*` 接口引用；
- 将 bundle 与 inventory 对比：377 条接口路径已登记，106 条为尚未登记的静态候选；
- 建立 252 条“页面/权限入口 → 操作 → 接口”关联基线（1 条敏感数据权限没有接口路径，因此只保留在权限操作表）。
- 已验证独立 Playwright 可完成 FAT 后台两步登录并持续复用同一浏览器会话；完整扫描脚本已捕获页面控件与 Network 请求。

本轮纠正后的三阶段扫描进度：

- 阶段 1 已完成：实时调用 `/admin/priv/list` 取得 12 个一级权限及 80 个一级/二级权限项，并与渲染侧栏的 11 个分组、3 个直达项核对；得到 57 个真实页面路由，0 个路由未解析。
- 阶段 2 已完成：同一 browser context 按 57 个侧栏路由只采集页面初始化与控件，共 844 条脱敏 Network 事件、78 个唯一 method+path，57/57 页面无错误。
- 初始化请求去重映射为 423 条 page/action/endpoint 记录：350 条 `ACTIVE`、72 条 `UNDOCUMENTED_ACTIVE`、1 条 `ACTIVE_FAILED`。失败项是登录页尚未建立鉴权时自动请求 `/admin/me/detail` 返回业务失败，保留原始事实，不用登录后的成功调用覆盖。
- 控件清洗后登记 679 个显式动作；已排除全局导航 tab、重复 selected 状态、动态统计伪 tab、无名称按钮及数据值伪按钮。615 个非写动作已逐项尝试，425 个实际交互、184 个因当前状态或严格 selector 安全跳过、6 个控件交互错误。
- 64 个写动作已逐项归档：3 个 `EXECUTED`、1 个 `NO_CREATE_REQUEST`、17 个 `BLOCKED_PREREQUISITE`、43 个 `BLOCKED_DATA_SCOPE`。执行项是本轮唯一 Marquee 的新增、编辑、删除闭环，三个写接口均 HTTP 200 / 业务成功，删除后目标不再可见；目标数字 ID 被通用脱敏规则过度脱敏，因此以唯一 marker 和目标行生命周期作为补充证据，不把该缺口隐藏。
- 最终动态接口去重为 109 个 method+path：89 个 `ACTIVE`、18 个 `UNDOCUMENTED_ACTIVE`、2 个 `MISCLASSIFIED`；2 个接口同时存在失败事件（登录前 `/admin/me/detail` 业务失败、无匹配筛选组合下 `/admin/game/search` 业务失败），但也在合法状态成功，因此 endpoint 汇总保留成功分类及失败计数，page/action 映射保留具体失败行。
- 长时间范围补扫完成 28/57 个重点列表、报表、日志、订单、审核和资金记录页：24 页取得非空响应，1 页扩大到页面已接受的 2020-01-01 起始范围仍为空，1 页在 90 天范围业务失败，1 页日期控件拒绝目标值，1 页仅 7 天请求成功为空而后续范围没有发出业务请求。共捕获 47 次业务查询（46 成功）、28 个唯一 endpoint；全部已存在于 109 个主扫描 endpoint 中，因此只补充时间范围和响应结构证据，不改变主计数。
- 会员记录级阶段已完成 17/17 个详情业务页签、11/11 个只读子入口和首批状态型写操作。本轮专用会员实际完成 Bet、Login Function Limitation 的 `Allowed → Forbidden → Allowed`、Risk Control 的 `status 0 → 1 → 0`，最终均恢复原态；Withdraw 基线已经是 Forbidden，因此如实保留为未验证写入。终止型会员已通过 `POST /admin/member/become/agent` 转为代理，详情接口确认 `is_agent false → true`。
- KYC 专用会员完成 `0 → 2（首提）→ 3（拒绝）→ 2（Re-KYC 重提）→ 5（通过）`。拒绝真实调用 `POST /admin/kyc/reject`，重提仍调用 `POST /member/kyc/v2/insert`，最终通过调用 `POST /admin/kyc/approve`。独立写操作资产现有 32 行、18 个唯一已触发接口，分类为 `ACTIVE 21`、`ACTIVE_FAILED 1`、`DOCUMENTED_UNVERIFIED 6`、`UNDOCUMENTED_ACTIVE 1`、`MISCLASSIFIED 3`；常规证据不保存截图，使用 DOM、Network 和脱敏详情状态。
- 会员列表内部操作已完成 30 个结论：22 个查询/筛选/分页只读动作、2 个行内只读入口、5 个 `BLOCKED_DATA_SCOPE` 和 1 个未捕获接口的 Export；Batch 实际发送 `POST /admin/member/list`，确认与 inventory GET 定义的 method drift 为 `MISCLASSIFIED`。会员详情 17/17 页签完成 DOM 清单，其中 14 个数据页签形成 72 个 UI 动作结论、76 条 action-endpoint 映射，40 个只读交互完成。独立合并后的管理后台当前动态面为 135 个唯一 method+path：`ACTIVE 113`、`ACTIVE_FAILED 1`、`MISCLASSIFIED 3`、`UNDOCUMENTED_ACTIVE 18`。
- 阶段 2 首轮虽完成 57 页，但发现 9 个表格按钮文本包含长数字记录标识，因此该轮未保留；增强脱敏后从零覆盖重跑，最终资产只包含一致的脱敏轮次。

真实 UI 扫描使用独立 Playwright，并在一次登录后持续复用同一浏览器。UI 只用于遍历页面、识别输入框/页签/按钮和触发真实请求；常规页面不截图。证据以 DOM 控件名称、Network 请求和必要的数据库只读核对为主，只有异常或重要写操作在确有必要时才另存脱敏截图。

管理后台同时提供中文和英文界面。扫描优先使用英文界面记录页面、页签和按钮的当前 UI 原文，同时保留权限树及原接口文档中的中文分类和名称作为对照；不因语言不同重复计算同一接口。FAT 会员详情已确认存在中英混合缺陷：英文会话仍显示“流水要求调整”“增加/扣除/清零”，推荐人变更被错误翻译为 `changed`。扫描器因此同时维护当前原文和语义别名，并结合字段上下文、弹窗标题及 Network 定位，不能把单一语言 exact selector 的失败当作控件不存在。故障说明见 [`../harness/known-errors.md`](../harness/known-errors.md)。

### 会员详情与流水游戏树

- 会员详情首页是拼装页：可见业务数据主要由 `GET /admin/member/detail`、`GET /admin/kyc/detail`、`GET /admin/finance/member/wallet` 三个接口提供；`GET /admin/priv/check` 负责操作权限判断，不计作首页业务数据源。这里的“三个”只指可见数据源，不表示首页总 Network 数量。
- 首页分为用户信息、推广、KYC、安全和统计等展示区。接口归属必须根据响应字段名和页面状态核对，不能把整个页面笼统归给单一详情接口。
- “流水要求调整”中的“流水游戏限制”是树形多选器，不是普通下拉框。层级为“所有游戏 → 游戏分类（Slot、Lottery、Table、Live、Arcade、Fish、Sport）→ 厂商 → 具体游戏”。扫描器必须按树节点语义展开分类和厂商，并区分初始加载、分类展开、厂商展开各阶段的 Network；不得用普通下拉 option 数量判断为空。
- 详情首页会预加载游戏树：`POST /admin/gameclass/list` 返回 7 类，`POST /admin/game/search` 以 12 个响应装载 5,731 个游戏（11×500 + 231）。打开“流水要求调整”时再次调用分类接口，并以一个 5,731 条响应装载完整游戏集合。当前聚合为 7 类、72 个“分类/厂商”组合、5,731 个游戏；展开分类或厂商没有新增游戏接口。后台壳的周期性 `/admin/sys/config/compliance/status` 不能归因到树节点。
- “General recharge rate”的铅笔入口按字段上下文定位；弹窗下拉只有 `Platform Configuration` 与 `Custom`，选择 `Custom` 后动态出现 `Custom Recharge Rate`。`operating record` 实际调用 `GET /admin/member/deposit/multiple/log?uid&page&page_size`，HTTP 200、业务成功；原文档示例中的 `operator_types` 当前 UI 没有发送。Custom 1.0 对应 `deposit_multiple_type=2`，恢复平台配置对应 `deposit_multiple_type=1`；`POST /admin/member/deposit/multiple/update` 的 Body 字段为 `deposit_multiple/deposit_multiple_type/google_code/remark/uid`。使用实时审批 TOTP 后恢复请求 HTTP 200、业务成功，详情从 Custom 1.0 恢复为 Platform Configuration 1.5，操作记录共 2 条，因此接口归类 `ACTIVE`。此前使用登录固定码的失败探针作废，不能用于接口失败分类。
- Credit/Debit 已使用本轮会员完成最小资金闭环：钱包 `0 → 0.01 → 0`，两次 `POST /admin/finance/adjust/insert` 均成功并由 `POST /admin/finance/adjust/list` 日志核对。Credit 动态要求选择“流水场馆/游戏限制”，本轮合法选择为“所有游戏”；Debit 恢复时不发送 Credit 专属的 `bet_multiplier/plats` 字段。
- VIP 手工调整完成 `V0 → V1 → V0`：两次 `POST /admin/member/vip/level/manual/upgrade` 均成功，首次变更约 12 秒后才由详情可见，并由 `GET /admin/member/vip/level/list` 的新增记录佐证；因此这类写接口必须等待最终一致性再断言。Token Wallet 列表 `POST /admin/finance/tokens/transaction/list` 返回业务失败，未继续调用调整接口。流水金额控件已用中英双语 label 与弹窗唯一 primary 按钮完成精确定位；`POST /admin/finance/turnover/add` 和 `/sub` 均 HTTP 200、业务成功，状态 `0 → 1 → 0`。增加分支选择全部游戏，数据库只读证据显示 `plats` 共 5,731 项；扣除分支游戏控件 disabled，不发送 `plats`。同一流水行最终 `state=2`、`finished=1.00`、`locked=0.00`，无遗留 active 流水；`clear` 未请求。

## 文件说明

| 文件 | 用途 |
| --- | --- |
| `fat-admin-page-inventory.csv` | 权限树得到的 68 个二级页面/入口，包含一级菜单、声明路径和下级操作数 |
| `fat-admin-static-routes.csv` | 当前 FAT bundle 中提取的 60 条候选 UI 路由；尚未逐页打开 |
| `fat-admin-permission-operations.csv` | 253 个下级操作权限及其与原 inventory 的匹配结果 |
| `fat-admin-page-action-interface.csv` | 静态权限/bundle 关联基线；最终动态主资产位于 `results/fat-admin-page-action-interface.csv` |
| `fat-admin-static-interface-comparison.csv` | 当前 bundle 的 483 条后台接口与 inventory/catalog 的路径级对比 |
| `fat-admin-api-evidence.json` | 脱敏 API 证据，只保存路径、状态、耗时、业务状态和响应结构，不保存响应数据、Token 或账号 |
| `fat-admin-baseline-summary.json` | 数量与 bundle SHA-256 摘要 |
| `admin-menu-probe-cases.csv` | 可复现的 12 个一级菜单子树只读探针 |
| `build-fat-admin-baseline.py` | 从临时原始证据重新生成上述脱敏资产 |
| `admin-playwright-full-scan.mjs` | 早期 bundle 路由探针，仅留作诊断；结果已明确作废，不进入最终资产 |
| `admin-menu-discovery.mjs` | 阶段 1：实时权限接口与渲染侧栏 DOM 路由核对 |
| `admin-page-initialization-scan.mjs` | 阶段 2：57 页初始化 Network 与控件盘点，不点击业务控件 |
| `build-explicit-action-inventory.py` | 清洗控件并生成显式动作、严格 selector 和风险分类 |
| `admin-explicit-read-actions-scan.mjs` | 阶段 3：按指定风险批次执行查询、页签、分页、详情等显式动作 |
| `admin-explicit-filter-actions-scan.mjs` | 仅对运行时确认属于查询容器的输入/下拉执行无持久化筛选探针 |
| `admin-long-range-scan.mjs` | 长时间范围补扫：逐级执行 7/30/90/365 天和页面已接受的最大观察范围，并校验日期控件实际值 |
| `build-long-range-results.py` | 合并主轮与精确重试，生成脱敏的长范围页面、操作和 endpoint 资产 |
| `admin-member-record-inventory.mjs` | 会员列表、Add Member 空表单、17 个详情页签及明确只读子入口扫描；不提交写操作 |
| `admin-member-current-target-probe.mjs` | 从 `/tmp` 仅运行时读取本轮 UID/手机号，完成列表结果行和详情 UID 关联及状态基线；原值不落盘 |
| `build-member-record-flow.py` | 合并会员只读轮次，生成操作接口、控件、Add Member 和写前置矩阵 |
| `fat-admin-endpoint-summary.csv` | 最终 109 个动态 endpoint 的唯一分类与成功/失败计数 |
| `fat-admin-page-action-interface.csv` | 最终页面 → 操作 → 接口映射（初始化、交互及写状态） |
| `fat-admin-inventory-comparison.csv` | 动态使用面与共享 inventory 的独立对比，不修改共享清单 |
| `fat-admin-write-action-status.csv` | 64 个写操作逐项状态、数据范围、前后状态及阻塞原因 |
| `fat-admin-final-summary.json` | 本轮最终数量、覆盖、分类及证据缺口摘要 |
| `results/long-range-page-summary.csv` | 28 个重点页面的范围、结果、阻塞范围和请求计数 |
| `results/long-range-page-action-endpoint.csv` | 日期筛选 → 真实请求映射；POST 请求体不可解时只记录编码和字节数，不推测字段 |
| `results/long-range-endpoint-summary.csv` | 长范围命中的 28 个唯一 endpoint 及原文档分类 |
| `results/long-range-admin-summary.json` | 长范围补扫汇总；明确不改变主扫描 endpoint 计数 |
| `results/long-range-admin-report.md` | 长范围结论和异常页清单 |
| `results/record-flow-member-action-endpoint.csv` | 会员列表、详情页签和只读子入口的操作 → 接口映射 |
| `results/record-flow-member-control-matrix.csv` | 列表行操作、17 个详情页签和 11 个只读入口的控件/风险/前置矩阵 |
| `results/record-flow-member-add-form.csv` | Add Member 12 个字段、必填标记与依赖；提交状态固定为未提交 |
| `results/record-flow-member-write-prerequisites.csv` | 会员写操作的当前目标、前置、恢复路径和阻塞分类 |
| `results/record-flow-member-summary.json` | 会员记录级阶段脱敏计数和当前 KYC 状态门禁 |
| `results/record-flow-member-report.md` | 会员记录级阶段可读摘要 |
| `results/record-flow-member-write-action-endpoint.csv` | 本轮专用会员/KYC 写操作的页面 → 按钮 → 接口、参数、前后状态和分类 |
| `results/record-flow-member-write-summary.json` | 首批写操作数量、恢复状态、终止状态和 KYC 状态链摘要 |
| `results/record-flow-member-detail-composition.json` | 会员详情首页三个可见数据源、权限请求和游戏树预加载关系 |
| `results/record-flow-member-turnover-game-tree.json` | 流水游戏分类 → 厂商 → 游戏层级、数量及展开阶段 Network 证据 |
| `results/record-flow-member-recharge-rate-controls.json` | 通用充值倍率编辑表单、动态 Custom 字段及操作记录真实请求 |
| `results/record-flow-member-recharge-rate-write-flow.json` | 通用充值倍率 Custom 状态、实时 TOTP 恢复请求、Body 字段和操作记录核对 |
| `results/record-flow-member-fund-pair-action-endpoint.csv` | 钱包 Credit/Debit 闭环、日志核对及 Token 失败分支映射 |
| `results/record-flow-member-reversible-vip-turnover-action-endpoint.csv` | VIP 可恢复闭环与流水调整未发送请求的逐操作结论 |
| `results/record-flow-member-gap-audit.md` | 会员列表/详情剩余内部按钮、方法漂移和陈旧状态资产审计 |
| `results/member-list-a-action-endpoint.csv` | 会员列表 Batch、筛选组合、分页、行内入口与 Export 结论 |
| `results/record-flow-member-tab-readonly-action-endpoint.csv` | 17 页签内部只读动作与导出请求映射 |
| `results/fat-admin-legacy-gap-review.csv` | 184 个安全跳过、6 个交互错误和 60 个旧写阻塞项的逐行复核 |
| `results/member-gap-merged-endpoint-summary.csv` | 本阶段独立合并的 135 个管理后台动态 endpoint；不修改共享 inventory/catalog |
| `results/record-flow-member-reversible-turnover-db-readonly.json` | 流水 `0→1→0` 的数据库只读完成态证据 |
| `build-member-write-results.py` | 从独立脱敏证据重建会员/KYC 写操作资产，不修改共享 inventory/catalog |
| `admin-shared-session.mjs` | 单次后台登录并生成 mode 0600 的临时共享 storage state，随后用新 context 验证会话 |
| `build-legacy-gap-review.py` | 从既有脱敏资产生成首轮跳过/错误/阻塞逐项审计 |
| `build-member-gap-merged-results.py` | 合并当前管理后台动态证据到独立结果，不写共享 inventory/catalog |
| `results/` | Playwright 独立扫描结果；不写入客户端截图目录 |

## 分类规则

最终分类严格使用任务定义：

- `ACTIVE`：必须有页面真实触发、请求成功及页面/数据核对证据；
- `ACTIVE_FAILED`：必须有页面真实触发及失败证据；
- `UNDOCUMENTED_ACTIVE`：必须有页面真实触发，且 inventory 中不存在；
- `DOCUMENTED_REACHABLE`：原文档存在，API 直连成功，但页面尚未发现；
- `DOCUMENTED_UNVERIFIED`：原文档或当前 bundle 有引用，但缺少合法参数、前置状态或 UI 证据；
- `STALE`、`REPLACED_BY`、`THIRD_PARTY`、`MISCLASSIFIED`：必须有逐页 Network、替代链路或调用端证据后再判定。

本轮额外使用 `UNDOCUMENTED_CANDIDATE` 作为临时状态，表示当前 FAT bundle 或权限树引用了路径，但 inventory 中没有记录，且尚无 UI Network 证据。它不能计作 `UNDOCUMENTED_ACTIVE`。

## 已验证接口基线

本轮实际成功执行：

- `POST /admin/login/auth`
- `POST /admin/login`
- `GET /admin/kyc/pending/count`
- `GET /admin/kyc/config/info`
- `POST /admin/kyc/list`
- `POST /admin/finance/deposit/risk/list`
- `POST /admin/finance/deposit/list`
- `GET /admin/finance/transaction/types`
- `POST /admin/finance/transaction/list`
- `POST /admin/finance/withdraw/risk/audit/list`
- `POST /admin/finance/withdraw/list`
- `GET /admin/me/detail`
- `GET /admin/priv/list`
- `GET /admin/group/list`
- `GET /admin/finance/payment/bank/list`

这些请求均为 API 登录或只读探针。除登录外，静态 bundle 中有引用且 inventory 有记录的接口暂记 `DOCUMENTED_REACHABLE`；待页面真实触发后才能升级为 `ACTIVE`。

## UI 扫描顺序

从当前 FAT 管理后台执行，不重新生成或覆盖共享资产。扫描严格分为三个阶段，上一阶段完成后才进入下一阶段：

1. **真实菜单发现**：登录后只处理左侧菜单。优先捕获实际 `/admin/priv/list` 权限接口，再展开渲染后的侧栏菜单；逐个读取菜单文字、DOM 层级和 anchor `href`，无 `href` 的叶子菜单通过点击后 `pathname` 获取真实 UI 路由。权限接口中的 `module` 可能是 API 路径，未经侧栏 DOM 核对不得当作 UI 路由。
2. **页面初始化与控件盘点**：严格按第一阶段生成的 `menu → page → route` 顺序，在同一 browser context 逐页访问。每页先只捕获初始化请求，再保存该页面当前可见的输入框、查询、筛选、页签、分页、详情、导出和业务按钮清单，不点击业务控件。
3. **显式交互**：只操作第二阶段在当前页面明确发现、并写入动作清单的控件。禁止坐标点击、禁止按通用选择器盲点全部按钮、禁止全局 `.ant-tabs-tab` 逐项点击；页签也必须先登记为该页面的显式动作。写操作必须使用本轮创建或用户明确指定的数据，并保存目标 ID、前后状态和核对证据。

长时间范围补扫只处理带明确起止日期和 Query/Search 控件的重点记录页。范围按 7、30、90、365 天逐级扩大，非空即停止；最后一档 2020-01-01 至扫描日必须先通过页面控件实际值校验并成功发出请求，因此只称“页面已接受的最大观察范围”，不宣称它是产品配置的绝对最大值。查询保持页面默认 `page_size`（观察到的 GET 列表请求为 20），不使用超大单页请求；本轮未另行点击第二页，分页动作覆盖仍以主扫描资产为准。请求体不可解时只保留内容类型和字节数，时间值由已校验的 UI 控件作为证据，不虚构 Body 字段。

失败接口原样归类并诊断，不调用后续成功接口制造通过。页面完成后更新独立结果目录中的映射资产，再统一决定是否合并共享 inventory/catalog。

Export 的动态完成标准是 UI 点击后捕获到真实导出请求；不要求在操作系统保存窗口继续确认，也不保存原始会员/资金明细。空结果导致业务失败时保留 `ACTIVE_FAILED` 操作证据和 `currently_used_by_ui=true`；如果同一 endpoint 另有成功 UI 事件，endpoint 汇总可保留成功分类。仅点击按钮或仅出现系统保存窗口、但没有 Network/download 事件时，记录 `CLICKED_NO_INTERFACE_EVIDENCE`，不得推断 endpoint 已触发。

### 作废说明

2026-09-03 早期按 FAT bundle 候选路由直接访问的 30/72 页探针未先完成真实侧栏菜单核对，并包含全局页签点击，因此明确标记为 `INVALIDATED_PROBE`，不得用于最终 ACTIVE/STALE/REPLACED_BY 判断，也不得合并到正式 page → action → endpoint 资产。它只保留为扫描器诊断记录；正式结果从上述三阶段流程重新生成。

扫描产物统一保存在本目录；`client-button-map/` 只保留客户端按钮说明和客户端截图。
