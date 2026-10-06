# Admin API Runbook

上级入口：[`API.md`](API.md) 和 [`api/p0/README.md`](../p0/README.md)。FAT/UAT 登录、账号和金额差异统一查看 [`ENVIRONMENTS.md`](ENVIRONMENTS.md)。本文件只说明后台鉴权与受控审批，不维护当前执行状态；实时状态看 [`AI-HANDOFF.md`](../../AI-HANDOFF.md)。

## 目标

记录后台接口自动化的登录、鉴权和调试规范。后台接口和客户端接口一样使用 CBOR 请求/响应，但登录字段和 header 更敏感，不能只照接口文档裸跑。

## 后台登录规范

后台登录需要两步：

1. `POST {{admin_url}}/admin/login/auth`
2. `POST {{admin_url}}/admin/login`

请求必须满足：

- `content-type` 使用 CBOR runner 时为 `application/cbor`。
- FAT 测试环境后台登录的 `google_code` 当前固定使用 `111111`。
- `google_code` 必须按数字发送，不要按字符串发送。
- `google_secret` 字段需要保留，当前可为空字符串。
- `x-device-id` 可从浏览器真实请求或环境变量注入；无人值守 runner 未收到 `ADMIN_DEVICE_ID`/`X_DEVICE_ID` 时，为本次进程生成新的 UUID，且不跨命令持久化。
- `client-id` 当前使用 `123`。
- `client-version` 当前跟随浏览器版本，例如 `Chrome/151.0.0.0`。
- `lang` 当前后台使用 `en`。

不要把真实账号、密码、Google code、token、cookie、设备 id 提交到仓库。

## 环境变量

以下`ADMIN_*`和登录入口属于主管理；独立代理管理与代理端的定位见[三套服务](#代理三套服务的只读定位)，不把一个登录token跨服务复用。

```bash
ADMIN_URL=https://admin-fat.filbet2025.com
ADMIN_EMAIL=<admin email>
ADMIN_PASSWORD=<admin password>
ADMIN_GOOGLE_CODE=111111
ADMIN_DEVICE_ID=<x-device-id from browser request>
ADMIN_GOOGLE_SECRET=
ADMIN_APPROVAL_TOTP_SECRET=<real approval totp secret>
ADMIN_APPROVAL_TOTP_ALGORITHM=SHA256
ADMIN_LANG_HEADER=en
ADMIN_CLIENT_ID=123
ADMIN_CLIENT_VERSION=Chrome/151.0.0.0
ADMIN_TOKEN_PREFIX=
```

注意：FAT 的 `ADMIN_GOOGLE_CODE=111111` 只用于后台登录。若目标环境后台登录也要求动态码，可将 `ADMIN_GOOGLE_CODE` 留空；runner 会优先使用 `ADMIN_LOGIN_TOTP_SECRET`，未配置时回退到 `ADMIN_APPROVAL_TOTP_SECRET`，算法同样优先使用 login 专用变量再回退到 approval 算法。充值补单、提现审核、KYC 审核等动作始终需要真实动态验证码，不能用 FAT 固定登录码代替。当前 FAT 与已验证 UAT 管理账号均使用 SHA256。

同一受控流程包含多个审核动作时，每个动作必须使用新的动态验证码。controlled runner 优先使用 `ADMIN_APPROVAL_TOTP_SECRET` 现场生成，并在检测到与上一个审核动作处于同一 TOTP 窗口时等待下一窗口；`.env` 中的 `ADMIN_APPROVAL_CODE` 只在没有 secret 时作为单次兜底，不能在 KYC、补单、清流和提现审核之间复用。

`ADMIN_TOKEN_PREFIX` 默认留空。前端真实请求里的后台业务接口使用裸 token：

```text
t: <admin token>
```

不是：

```text
t: t:<admin token>
```

## 已验证命令

```bash
ADMIN_EMAIL=<admin email> ADMIN_PASSWORD=<admin password> ADMIN_GOOGLE_CODE=111111 ADMIN_DEVICE_ID=<x-device-id> \
python3 scripts/api-smoke-runner.py \
  --admin-login \
  --execute \
  --insecure \
  --body-format cbor \
  --out /tmp/admin-login-cbor.json
```

成功标准：

- `/admin/login/auth`：HTTP 200，业务 `status=true`。
- `/admin/login`：HTTP 200，业务 `status=true`，`data` 为后台 token。

## 已验证后台只读探针

以下接口已在 FAT 调试通过，可作为后台 P0 候选：

| 接口 | 结果 | 断言建议 |
| --- | --- | --- |
| `GET /admin/me/detail` | 通过 | `status_true,data_object` |
| `GET /admin/finance/payment/bank/list` | 通过 | `status_true,data_object,keys:data.d\|data.t\|data.s` |
| `GET /admin/finance/transaction/types` | 通过 | `status_true,data_list` |
| `GET /admin/kyc/pending/count` | 通过 | `status_true` |
| `GET /admin/kyc/config/info` | 通过 | `status_true,data_object` |
| `GET /admin/priv/list?pid=0` | 通过 | `status_true,data_list` |
| `GET /admin/group/list?page=1&page_size=20` | 通过 | `status_true,data_object,keys:data.d\|data.t\|data.s` |
| `POST /admin/kyc/list` | 通过 | `status_true,data_object,keys:data.d\|data.t\|data.s` |
| `POST /admin/finance/deposit/risk/list` | 通过 | `status_true,data_object,keys:data.d\|data.t\|data.s\|data.summary` |
| `POST /admin/finance/withdraw/risk/audit/list` | 通过 | `status_true,data_object,keys:data.d\|data.t\|data.s\|data.summary` |
| `POST /admin/finance/deposit/list` | 通过 | `status_true,data_object,keys:data.d\|data.t\|data.s\|data.summary` |
| `POST /admin/finance/withdraw/list` | 通过 | `status_true,data_object,keys:data.d\|data.t\|data.s\|data.summary` |
| `POST /admin/finance/transaction/list` | 通过 | `status_true,data_object,keys:data.d\|data.t\|data.s` |

当前 FAT 后台测试账号的 `/admin/me/detail` 中 `roles` 可为空字符串，不能以 `roles` 非空作为登录或权限成功标准；权限断言使用 `group_id`、`button_permission_ids` 字段存在，且 `button_permission_ids` 非空，再结合 `/admin/priv/list` 权限树查询。

只执行后台 13 条 safe smoke：

```bash
python3 scripts/api-smoke-runner.py \
  --cases api/p0/test-cases.csv \
  --with-admin-login \
  --base admin \
  --execute --insecure --body-format cbor \
  --out /tmp/admin-p0-smoke.json
```

后台列表 POST 请求不能发送空 body。充值/提现待审列表和财务记录使用 `start_time`、`end_time`、`page`、`page_size`；提现待审 `/admin/finance/withdraw/risk/audit/list` 使用毫秒，不能把其他列表的秒级参数直接复用。`test-cases.csv` 使用动态时间标记，由 smoke runner 在发送前替换。

UAT 会员账号筛选的实测契约：

- 浏览器页面路由为 `/member-center/list` 和 `/member-center/detail/{uid}`；它们不是数据接口。会员列表数据接口是 `POST /admin/member/list`，使用 CBOR 请求体且至少包含 `page`、`page_size`；直接 `GET` 返回 405。
- `kyc_status` 筛选值必须按字符串发送，例如 `"5"`；按整数发送会得到业务失败。
- `/admin/member/detail?uid=...`、`/admin/kyc/detail?uid=...`、`/admin/finance/member/wallet?uid=...` 均为只读 GET，可分别核对会员、KYC、流水和钱包状态。
- UAT lane 准备以后台接口为主：先从会员列表批量筛选，再用三个详情接口核对 KYC、余额、可提现额、锁定状态、剩余流水、钱包密码和最近登录状态。具体账号年龄、号段和复核规则统一见 [`ENVIRONMENTS.md`](ENVIRONMENTS.md)，不要在本文件重复维护。
- 后台字段足以完成候选筛选，但不能证明客户端 token 当前可签发，也不能完全替代客户端 `/finance/account/list` 的提款账户契约；列表中的 password 信息不是可复用明文。
- UAT `/admin/sms/auth?code=<current admin TOTP>&id=<sms id>` 已验证为只读短信验证码查看接口，成功时 `data` 为 6 位验证码。设置 `CLIENT_OTP_SOURCE=admin_sms` 后，客户端 runner 会在申请短信取得 id 后通过该接口在内存中取码并登录；验证码不得写入结果、日志或环境文件。

## 代理三套服务的只读定位

2026-10-05用户授权整体摸底时，FAT三套服务及正常登录已分别验证。日期结果与边界见[代理模块](../../modules/agency/verification-20261005.md)，本节维护后续定位方法；不推广为UAT可用，也不将业务true当作功能验收。

| 服务 | FAT地址 | 登录与查询定位 |
| --- | --- | --- |
| 主管理 | `https://admin-fat.filbet2025.com` | `/admin/login/auth`→`/admin/login`；代理统计`/admin/reports/agency`，会员统计`/admin/reports/member` |
| 独立代理管理 | `https://admin-agency-fat.filbet2025.com` | `/backend/agency/login/auth`→`/backend/agency/login`；代理、会员、申请列表位于`/admin/agency/`，自身资料与权限位于`/backend/agency/` |
| 代理端 | `https://agency-fat.filbet2025.com` | 现有会员短信验证后`/agency/otp/login`；自己的名单／看板／统计位于`/agency/` |

独立管理本轮沿用忽略环境文件中`ADMIN_EMAIL/ADMIN_PASSWORD/ADMIN_GOOGLE_CODE/ADMIN_GOOGLE_SECRET`，Google code按整数发送；token只留该服务会话内存。主后台`Session.login()`只实现主管理两步路径，不能直接当独立管理登录。独立管理认证适配、三端base/token区分尚未接入通用smoke入口，不新增可执行命令承诺。

已定向校准的查询差异：

- 独立管理佣金阶梯用`GET /admin/agency/ladder?settle_type=1/2`（周／月）。Bruno示例的`type`会返回混合配置，不沿用为周期断言。
- 权限路径完整为`GET /backend/agency/priv/list`，不能丢`backend`段。活跃条件读口为`GET /backend/agency/sys/config/active/list`；`/backend/agency/sys/config/list`是三开关，添加`ty=4`不改变该响应。
- 独立管理财务列表`POST /agency/finance/transaction/list`使用CBOR body中的`uid/start_time/end_time/page/page_size`，时间为毫秒。仅POST query的文档样例本轮返回EOF，不沿用空body。
- 主管理会员个人统计的所属代理筛选实际字段为`agency_upline_name`。TEST-3220附件的真实请求与UI／API一致；每轮按当前直属UID集合验证隔离，不能用邀请人筛选替代。日期结果见[BUG回归](../../modules/agency/regression-20261005.md)，不沿用初轮混入其他代理的结论。
- 代理账号空白时先用精确UID对照会员详情、独立管理账号与基础库，再查原始统计响应。UID按十进制字符串比对，避免18位ID转浮点；代理统计账号筛选使用`user_name`，独立代理列表使用`username`，不凭同名页面猜参数。分别查询问题日和区间、有／无账号筛选，检查同UID是否被空名／有名拆成多行及筛掉的数据；所属代理`agency_upline_name`与邀请人`parent_username`分别核对。涉及注册时只读核`fb_members`与`fb_report_basic_member`的上级UID／姓名及`is_reg`，区别身份绑定和报表姓名快照。新旧响应均标采集时间，部分名字恢复不判全量修复。MySQL表、Doris与在线响应分别记录，不能只因结果相似断言当前消费链；需要写入实现和当前后端SQL／同步证据才能确定完整根因。
- 三开关同时核`current/target/open_time`；文档规定按生效时间选current或target。开关开启或佣金列表为空都不能证明后台停算停发。

代理注册归属定向复现时，先读代理模块来源并精确核推荐码状态／有效期、所属`uid`、域名类型／启停／所属代理及三开关。邀请码行的`parent_uid`不作为新会员结果；对本轮新会员核主档上级、一级关系树及代理直属名单。至少区分域名停用时推荐码、域名启用时无参数、域名启用时与另一代理推荐码冲突三个条件；使用未注册测试号且不追加KYC或资金操作。真实网页保留URL与推荐码表单观测，必要时核当前客户端资源：`u`生成注册body的`invite_code`，`domain`为入口`window.location.host`；好友邀请`i`是另一维度。现有`RegistrationOperations`未默认发送域名头，不能省略该前置来判断域名规则失败。临时启用共享主域名会影响同期新注册，执行前明确具体映射及恢复状态；结束后通过页面和只读来源确认恢复，数据库始终只读。

当前inventory/catalog把`angency`（独立管理）和`angency1`（代理端）归到同一`agency_url`，smoke共用`AGENCY_URL/AGENCY_TOKEN`，还存在相对权限URL丢段。只用于检索与显式校准，未修正前不直接批量执行。GET里有谷歌解绑和logout；只读授权不包含这些动作。未知素材body、路由及周期编码先核真实契约，禁止审批／余额调整／配置修改探针。

### 代理BUG回归的对账与页面条件

用户已明确独立代理管理首页不展示本次数据；整体回归跳过其首页／BI／图表接口。代理自己的首页属于2100范围，不能一同略过。先固定当前全部直属UID集合、窗口与采集时间；旧M1／M2／M0只是子集，同期其他测试新增会员必须分列，不能将金额变动误报。有效投注按已结算type1／3，GGR按正文不分bet_type，普通／FS／JP分别留源，避免套用同一类型过滤。

代理统计使用同一GMT+8窗口分别取全量、实际20条分页、精确账号筛选；累计会员不随区间改变，各页集合去重比较，金额小计按当页、总计按全量，比例字段按定义计算。UI要等明细加载完成，不能以先变化的页码判结果。另从第2页改变代理筛选，核页码／总数重置与命中行；正常翻页通过不能覆盖这一场景。点击代理下钻核目标页、代理及起止日期，不只检查URL路径。

真实导出先保留实际下载文件，再按账号／十进制UID核行集合、金额、所属代理UID／账号值及代理端遮蔽；只有表头或“导出完成”提示不判通过。姓名为分段对象时分别核接口非空遮蔽值、页面与CSV，不能把有姓名的会员显示／导出空值当成遮蔽通过。标准下载事件捕捉超时可按本次文件名／时刻核默认下载目录的新文件；主管理若使用原生保存窗口且桌面连接不可用，记录未取得文件与实际日志，交用户保存后续验，不用API生成CSV替代产品导出，也不因工具未完成保存报产品漏行。定向回归证据见[10-05记录](../../modules/agency/regression-20261005.md)，未接入通用CLI。

## 主管理直接开通业务代理

2026-10-05当前会员页源码已核：主管理使用`POST /admin/member/become/agent`，CBOR body为`uid`（新会员精确UID）、`acc_type=1`（页面固定参数）、`settle_type=1`（周结）及整数`google_code`（实时审批TOTP）。当前页面结算方式固定默认周结；`acc_type`在既有代理编辑契约中是净盈利历史累计设置，不能直接把1翻译为代理状态正常。`/admin/superior/update`是转线，不用于成为代理；后台员工授权也不等于会员代理资格。

执行需明确批次授权，只对本批新会员开通。注册沿用号码查重与游标能力；每次开通通过公共审批码能力等待新TOTP窗口，不复用固定登录码。开通成功后核同UID／手机号的客户端资格、KYC状态、代理配置及通过审核记录；未认证会员的FULLYKYC联动按[代理规则](../../modules/agency/README.md#身份关系与审核边界)核对。创建／开通已返回成功而后续查询中断时，先只读核已有身份，不重放写请求。

代理列表及审核记录查询当前仍属于独立代理管理host，分别用`GET /admin/agency/list`的`username`筛选和`GET /admin/agency/audit/list`，再按十进制UID精确匹配；主管理同路径本轮返回404。列表即时为空时保留该响应，进行有上限的只读复查并对照基础库，不把空列表当成开通失败或重新开通。当前合同与定向验证见[10-05记录](../../modules/agency/verification-20261005.md#追加15个新业务代理)。此流程尚未接入通用CLI或P0门禁。

## 新代理在统计报表中的可见性

代理身份列表与主管理统计报表分开核对。开通后先查独立代理管理列表确认资格；统计报表按日期查`GET /admin/reports/agency`，账号筛选字段为`user_name`。仅因统计报表无行，不能判代理未开通或重新开通。

2026-10-05定向查询已有“直属注册1、充值金额／次数0”且可见的代理样本，说明充值不是出现报表行的必要条件。创建新下线时先核主档上级、关系树、注册日报和同日期代理统计，再决定是否增加充值样本；未实测的新增下线不提前判可见。同步容差沿[2100 Q-05](../../requirements/ISOP-2100/questions.md#q-05)，保留采集时间。随后已定向验证新代理通过推荐码注册1个直属后，零充值即可同时出现在独立直属名单、主管理统计API及页面，见[最小样本记录](../../modules/agency/verification-20261005.md#追加实测ag01注册1个直属后零充值可见)。当前服务端完整取数SQL未取得，不把样本观察写成“所有零业务代理必须隐藏”的产品规则，也不为显示报表先批量制造充值。

用户明确授权批量准备直属会员后，逐代理核当前推荐码、手机号和真实上级，已成功记录只读复查并跳过。号码游标保存的是最近分配候选；连续批量注册时，下一起点还须大于本批已成功使用的最大号码，不能只依赖即时列表查重，避免新会员索引延迟造成重复候选。注册前落盘尝试边界，业务失败停止；本地分配拦截且尚未发短信／注册的号，可确认日志后继续未开始部分。该批处理仍是定向操作，未接入通用CLI。

统计与名单查询各自保留时间及日期窗口。UID拒绝浮点并按十进制字符串匹配；精确账号筛选核完整响应是否只含目标，不能先截取目标子集再声称筛选正确。独立直属名单同时核顶层`parent_uid`与嵌套`parent.uid/username`；主管理会员详情当前不返回`parent_name`，姓名交叉核客户端主档或独立名单。日报或在线行未齐只做有上限的只读等待，不增加注册或充值来强行显示。

## 主管理历史调试问题

之前后台 token 失败不是接口不可用，而是 runner 没有完全复刻前端请求：

- 缺少或未注入 `x-device-id`。
- `google_code` 被作为字符串发送，后端期望数字。
- 曾误以为后台接口需要 `t:` 前缀，实际前端业务请求使用裸 token。
- runner 曾把业务失败响应里的字符串误判成 token，现在只在 `status=true` 时提取 token。

## 维护与复核顺序

1. KYC 按本次 uid 精确定位记录，复核后台审核与客户端状态；驳回重提矩阵属于扩展专项。
2. 业务审批使用真实动态令牌，只处理当前 flow 创建的记录。
3. 订单关联核对 uid、订单号、金额和状态；账变及最终出款的验收层次按环境手册区分。
4. 用 `--base admin` 独立定位后台 safe smoke 失败；当前工程下一步只维护在交接中。
