# ISOP-2090定向只读与受控配置能力

[需求设计](../design.md) · [功能用例](../test-cases.md) · [后台契约](../../../api/runbooks/ADMIN.md)

2026-10-12已实现活动初采、公开源码取证、输值返利日报、客户端定向只读采集及受控配置保存／精确恢复。当前没有本单`plan.json`；这些命令不接入默认P0或`qa:requirement`，结果只覆盖关联C用例的API子项，不将复合功能用例整体判PASS。10-13指定统计日复验从[当前记录](../verification-20261013.md)进入；昨日实际结论及未测边界保留在[10-12记录](../verification-20261012.md)。

## 顺序与命令

先执行需求证据检查，再核选中FAT配置与本轮后台登录码；已有账号不重建。后台与页面同账号串行接力，执行期间不在另一入口重新登录。命令默认离线，不读取或输出凭据；实际采集需要显式`--execute`。

```bash
npm run qa -- evidence ISOP-2090
python3 requirements/ISOP-2090/api/initial-read.py
python3 requirements/ISOP-2090/api/run-readonly.py
python3 requirements/ISOP-2090/api/run-readonly.py --env .env.fat --execute --insecure
```

`initial-read.py --execute --insecure`只fresh后台登录，并查询既有`GET /admin/promo/list`的“输值”名称和全量首100项；不保存配置。日报suite只fresh后台登录一次，随后读取`GET /admin/promo/nl/list`：100条参考、10条完整分页、10-07—10-11日期、精确会员/VIP/分级筛选、不存在UID、missing/invalid鉴权，以及历史冻结行的内部金额与人数关系。账号、手机与UID在公开结果中用M/R别名；完整参数和响应保存0600私有文件。

次日复验使用显式`--stats-day YYYY-MM-DD`，只接受有横线的有效日历日期，非法日期或时间字符串在登录前拒绝。该模式给基线、分页、日期／会员组合筛选、不存在UID、鉴权及末次GET统一加`stime=etime=指定日`，所有成功分页的行日期必须属于指定日；混日响应立即停止依赖断言。日期探针只查询指定日，保留统计日与UID／账号／手机／VIP／分级组合，不以未采参考的邻日空集推定通过。没有此参数仍沿用旧全量及10-07—10-11探针，不能直接当新日结果。`--out`在执行入口先转为绝对路径，支持仓库reports内的相对或绝对目录，避免首次留证时路径比较失败。

```bash
python3 requirements/ISOP-2090/api/run-readonly.py --stats-day 2026-10-12 --out reports/qa/ISOP-2090/20261013-rebate
python3 requirements/ISOP-2090/api/run-readonly.py --env .env.fat --execute --insecure --stats-day 2026-10-12 --out reports/qa/ISOP-2090/20261013-rebate
```

本模式新建日期批次，报告记录指定统计日及实际采集时间，金额只核本日行的冻结`conf/upper_limit/lower_limit/multiple`，不拿当前活动配置或旧日上限代替。空日金额、门槛、唯一性、分页和人数汇总保持NOT_RUN；结构、空筛选与鉴权可独立核。旧10-07—10-09明细／流水失败留在原日期证据中，不计为新日失败，也不由新日通过推定历史缺陷修复。`created_at`只表示本轮返回字段，不证明05:00调度、自动执行或覆盖全天任务；这些需要独立任务时点及资金源对账。指定日不能与保留原范围的`--reassess`同时使用。

10-13目标日只读采集已取得独立礼金、账变余额差及关联活动流水，完整结论见[当天记录](../verification-20261013.md)。财务链匹配错误的实派金额不能覆盖全活动封顶失败；本日实派×倍数一致不声明历史分差修复。当前编辑器三组均显示“启用”，只证明采集时`state=0`的UI语义；源净输1999／日报2000及缺负规则保留历史配置／归属待核线索，不据此判C04失败。用户确认无人手工触发或造样本，仍未取得05:00任务来源和派发前余额。

10-12原始证据、公开JSON与HTML/CSV在忽略的`reports/qa/ISOP-2090/20261012-full/`；10-13指定统计日复验统一用`reports/qa/ISOP-2090/20261013-rebate/`。每次采集新建`api-readonly-<timestamp>`，不会清理既有P0或覆盖旧证据。报告子项关联C01/C02/C03/C08/C14/C19；读取报表算术不证明独立注单、奖金入账、账变、流水源、05:00自动派发、恢复重跑或真实CSV通过。未登录保护不替代低权限角色授权与跨会员隔离。

公开基线含`coverage_features`，明确是否含负净输、多规则、上限0、正门槛与非正净输样本；金额、门槛、唯一性、汇总和分页在空基线时保持NOT_RUN。稳定`check_key`用于离线重分类，旧报告从原用例名称迁移，不能依赖执行序号。明细金额不符归C14子项；没有负净输样本时不据此判C04整卡失败。

离线重分类既有证据，不再次登录或发送GET：

```bash
python3 requirements/ISOP-2090/api/run-readonly.py --reassess <原api-readonly目录/result.json>
```

10-12当前测试上下文将10-07两条记录识别为提测前种子/旧配置版本，100倍比例差异保留为历史不一致待确认，不直接判当前算法BUG。公式产生亚分金额而报表两位显示的差异保持精度未决，不指定舍入算法。已实派×倍数不等于打码金额的候选单独保留，独立入账/流水源证据由实际对账另行提供。重分类生成新目录并保留原目录，仍引用原采集时间和私有响应。

客户端必须与同账号H5页面串行，密码登录会令旧会话失效；只登录客户端、不登录管理员。先传已留的后台活动列表私有快照，再执行详情与真实前端fallback两个GET。`--recorded`只分析已采集两GET，无新登录、无新请求；新报告采用`recorded-readonly-reassessment`，保留原`source_time/source_run_id`，将复核时间记入`classification.reviewed_at`，并明确`network_requests=0`。第一次名称过滤快照为空，应使用包含ty41的全量活动快照，不能补猜业务接口。

```bash
python3 requirements/ISOP-2090/api/run-client-readonly.py --admin-snapshot <已留admin-promo-list-private.json>
python3 requirements/ISOP-2090/api/run-client-readonly.py --execute --insecure --admin-snapshot <已留admin-promo-list-private.json>
python3 requirements/ISOP-2090/api/run-client-readonly.py --recorded <原client-readonly目录/result.json> --admin-snapshot <已留admin-promo-list-private.json>
```

客户端采集公开响应字段类型、游戏目录ID及合规属性、比例和富文本长度/hash，原始响应仍为0600。旧后台快照与当前客户端的时点差异、合规header变化、目录属性含义未确认时不能定推荐失败。合规校验与推荐来源映射只关联C16 API子项。

真实客户端采集出现脚本错误或业务断言FAIL时退出1；成功退出0仍须查看各子项及未测边界。离线`--recorded`成功完成分类时退出0，仅表示分析完成，不表示原业务结果通过。

## 受控配置与恢复

`run-config.py`默认只输出dryrun合同。执行限定`.env.fat`的两端FAT主机，必须同时指定`--execute --fat-guard ISOP-2090-activity41`；本环境按已接受的TLS例外加`--insecure`。同账号后台页面与API仍串行。当前已知重复组名会被服务接受，本批已停止其余负例，不再执行默认整批；修复后的定向回归另行限定范围。

```bash
python3 requirements/ISOP-2090/api/run-config.py
python3 requirements/ISOP-2090/api/run-config.py --env .env.fat --execute --fat-guard ISOP-2090-activity41 --restore-from reports/qa/ISOP-2090/20261012-full/config-directed-20261012T170840632233/result.json --insecure
python3 requirements/ISOP-2090/api/run-config.py --env .env.fat --execute --fat-guard ISOP-2090-activity41 --marker-only --insecure
```

每次POST前fresh GET核CAS；恢复只允许当前完整业务状态精确匹配本次记录的候选，或已等于原基线，仅忽略`updated_at/updated_uid/updated_name`。未知额外字段或外部更改不覆盖；后端未提供原子版本锁，读取到写入之间的竞态仍是边界。POST异常不重试，最多尝试一次恢复。登录码、token不落盘，证据请求body省略`google_code`，完整响应0600。

| 本批操作 | 原始证据 | 已证实范围与边界 |
| --- | --- | --- |
| 配置校验 | `config-directed-20261012T170840632233/result.json` | 同值保存读回、跨组重复游戏与空组名拒绝已核；重复组名HTTP200／status true且读回只有`config.games`精确变成候选，保留C18 FAIL／BR-04。首次异常接受后停止，超20字组名及负门槛／上限／倍数／组比例／VIP比例未执行，原marker也跳过 |
| 单独恢复 | `config-directed-20261012T171159147797/result.json` | candidate归属与fresh CAS成立后，一次POST恢复，全部业务字段回到原基线；这是清理成功，原负例FAIL及缺陷不变 |
| 独立summary marker | `config-directed-20261012T171326673083/result.json` | 仅原基线→唯一marker→单次fresh client三GET→精确恢复，无负例；验证C15 API富文本动态同步，管理员及客户端恢复后与17:08基线一致，不提升H5／App整卡结果 |

原配置批首次在恢复等待码时中断，原`result-interrupted-original.json`保留；加强候选归属守卫后另批清理。marker已完成并恢复，随后本地HTML渲染长证据串异常；只使用留存0600响应离线重建，未补打业务请求。

## 2026-10-12当前前端合同

| 操作 | 方法与路径 | 已读参数/响应 |
| --- | --- | --- |
| 活动列表 | GET `/admin/promo/list` | `page/page_size/activity_name`；本轮已定向采集ty41活动；初采全量只取首100项 |
| 配置保存 | POST `/admin/promo/update` | ty41映射`kn`组件，提交首步表单+`ty/multiple(string)/google_code(number)/config(JSON string)/summary`；只读suite不调用，受控保存见上节 |
| 输值日报 | GET `/admin/promo/nl/list` | `page/page_size/username/uid/phone/vip/level/stime/etime`；日期为`YYYY-MM-DD`，VIP为字符串数值，level为bronze/silver/gold/platinum/diamond；组件不附加activity_id/pid |
| 日报导出 | GET `/admin/promo/nl/export` | 同表单筛选加`page=1/page_size=1000/topic_id`；此suite不调用、不代替真实UI CSV |
| 明细 | 主行`conf`解析 | JSON字符串或数组，不存在本页独立detail请求；页面规则返利优先读`bonus`，否则`capped_amount` |
| H5活动详情 | GET `/promo/net/loss/detail` | 无pid/query；`data`含`start_time/end_time/cur_time/state/conf/detail/game_list`，本轮`conf`为数组、`game_list=null` |
| H5推荐fallback | GET `/member/game/listRw` | `game_types=3/page=1/page_size=10/sort=Popular/query=''`；目录行在`data.d` |

日报响应必须解码为业务成功对象：`body.data.data`是行数组，`body.data.t`是总条数，`body.data.s`是汇总对象。空集支持`data=null/t=0`；`data.d`不属于本页合同。主行字段为`stats_day/created_at/valid_bet_amount/payout_amount/net_loss_amount/capped_amount/bonus/lower_limit/upper_limit/multiple/multiple_amount/conf`及身份字段；汇总核`num/net_loss_amount/bonus/multiple_amount`。明细字段为`game_id/group_name/name/valid_bet_amount/payout_amount/net_loss_amount/rate/bonus/capped_amount`；空game_id按基准规则展示，非空按指定游戏展示。

10-12已读导出共享组件先等待`openStream(fileName)`的原生保存窗口，再调用导出调度并通过MQTT写流；该版本窗口取消的`AbortError`发生在调度前，不能判后端导出失败。10-13未刷新返利当前报表／导出bundle，今日导出范围以实际页面、日志和保存文件为准，不以昨日源码证明今日请求数。完整CSV必须由页面实际保存并复核。

ty41配置序列化`zc`保留其余原配置并重写：`venue[{name,game_class,rebate_ratio:[{level,ratio}]}]`、`games[{name,list,rate,state}]`、去重`exclude_games`、第三步`lower_limit/upper_limit`、展开`turnover_limit`、`activity_range/user_list/source_rule/popup_text`，固定`order_review=1/received_type=2`。倍数在活动顶层，删除历史config.multiple。名称trim≤20、比例/金额转字符串、level小写、state为0/1、全会员范围清空名单均属于实际归一化；同值保存必须独立核前后，不能假设完全字节不变。有效片段为`ty41-loss-rebate-save-contract-verified.txt`。早期`ty41-save-contract-snippet.txt`实际是同chunk的ty40 Cashback `nc/sc`，已明确标错，不作为2090写入合同。

实际保存传输以本轮admin主bundle拦截器为准：`umi-d433ca66.js`的`pqr()`在POST且`!notEncode`时执行`e.data=b2(e.data)`，`To=yqr(...pqr(),gqr())`将该拦截器挂到请求；`promoUpdate`仍声明`Be.Json`，所以本请求保留`application/json`标头而body实际为CBOR。证据为`evidence/source/ty41-admin-transport-verified.txt`，对应`20261012T162401424064-umi-d433ca66.js`的offset 3481318；不能单从标头推断JSON编码。

客户端资源`hov 4f2449b7`：详情`game_list`经normalizer后要求非空code和img；有有效详情游戏时最多取前10，不补齐；无有效游戏或详情失败时请求Slot Popular前10。组件不直接读取后台第一组/state，也不在组件层按compliance过滤。More Games固定到`/s-game/category/3?sort=Popular`。VIP表读取详情conf并按五级排序；T&C优先读取详情detail，有文本清理但不根据最新比例自动改写旧正文。

## 源快照与实现

公开源码采集器为`static-sources.py`，仅GET选定FAT域的`/`、`/assets/*.js`、`/_nuxt/*.js`；client还允许HTML已观察的固定`pwa.filbet.com/filbet/dev/v20260129/assets|modules/*.js`。不登录或携带token，用`NoRedirect`在发送跳转目标请求前拒绝重定向，默认有数量/大小上限。显式`--asset`可下载已观察的静态chunk；HTML fallback不视为有效JS。首次引用解析存在`assets/assets/`路径重复，所得HTML保留在证据中，后续修正并以真实有效JS为合同来源。

| 2026-10-12有效公开源 | SHA256 |
| --- | --- |
| `umi-d433ca66.js`：SDK nl/list、nl/export、promo/update | `03797e50187548d918f78a0adbee4a6e06e6586a11e86579f1f6190ead0440fd` |
| `index-0daee2f9.js`：ty41配置/日报/明细/筛选 | `acc738da5bbea8fb79d861710940cd385c43df7f013e361cae28158db92093c1` |
| `index-3f1ae5ae.js`：导出窗口与调度 | `27a17b4530753676d06c0983c6a7035131e273985d237f46f6f2a0ee765c6c9a` |
| `index-Cucz2P_Y.js`：hov4f2449b7 H5详情、VIP、T&C、推荐与More Games | `1ac40d83556d29199e266439ebd1876c48c5634c34c0eb7dff0a1df143fca9d8` |

10-13另有7次钱包相关公共GET，两个旧资源返回HTML，未作为JS合同；已读当前`umi-24487e02.js`、`index-d1380e3f.js`、钱包`detail-a7608baa.js`及实际字典`4001 Bonus`。原始文件与manifest留`reports/qa/ISOP-2090/20261013-rebate/evidence/source/`。本次只证明当前admin bundle已变化及钱包字段／字典定位，不证明返利报表／导出实现与昨日相同、奖金专用钱包归类或后端部署；上表保留10-12来源日期，不冒充今日版本。

完整快照在`evidence/source/`，公开报告保存来源路径与hash；源码证明请求/展示实现，不证明业务规则正确或实际取数通过。共享逻辑在[`scripts/filbet/loss_rebate.py`](../../../scripts/filbet/loss_rebate.py)、[`loss_rebate_client.py`](../../../scripts/filbet/loss_rebate_client.py)及[`loss_rebate_config.py`](../../../scripts/filbet/loss_rebate_config.py)，本目录CLI只负责参数。定向离线fixture验证真实结构、Decimal精度、鉴权不泄露、分页去重、空基线未测、覆盖缺口、公开脱敏、客户端code/img资格、离线采集来源及配置恢复守卫。

```bash
env PYTHONPATH=scripts python3 -m unittest discover -s tests/unit -p 'test_loss_rebate*.py'
```
