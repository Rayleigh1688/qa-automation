# FAT核心表取数说明

核查日期：2026-09-29；数据库只读。来源为本轮information_schema、匿名时间样本与登录聚合，以及2092明确标日期的历史执行。最新结构使用[查询模板](inspect-structure.sql)刷新。本页不维护实时通过率。

## 数据分布与关联

| 表 | 用途/逻辑关联 | 核对要点 |
| --- | --- | --- |
| fat.fb_members | 会员主表，uid关联登录、充值、提现 | last_login_at为可变最新值，不能重建历史日登录；first/second/third_deposit及deposit_count用于状态转换交叉核对 |
| fat.fb_members_login_log | 登录日志，uid为会员/账号关联标识 | 来源由用户确认；created_at为秒，不能复用会员表毫秒条件；注册及代理操作也在此表 |
| fat.fb_deposits | 充值订单，uid关联会员 | status、gt、save_ty、amount、paid_amount、created_at和paid_at分别核对；按指标选择字段；2092充值统计用户确认取amount，不取paid_amount |
| fat.fb_withdraws | 提现订单，uid关联会员 | 完成状态、save_ty及申请/到账字段分开；历史差额曾由系统生成单混入造成 |
| fat.fb_members_balance / fb_members_balance_new | 钱包表 | 存在旧/新口径，balance为decimal(20,8)；本轮只读结构，未确定每种页面取哪张表 |
| fat.fb_balance_transaction | 账变 | created_at为bigint，state注释仅场馆业务使用；非全表通用“支付状态” |
| orders.tbl_game_record | 主注单，uid关联会员，prefix区分环境 | bet_amount投注、net_amount玩家输赢、jp_winning奖池派彩，金额decimal(20,8)；结算state与settle_time联合核对 |
| orders.tbl_game_record_sport | 体育分离注单 | 与主注单可能重叠，不能直接UNION ALL求和；先按环境及订单标识核查重复，旧样本对账见2092 |
| fat.fb_report_basic_member / fb_report_balance | 会员基础及余额报表表 | 结构存在、MySQL缺行均不能证明Doris同名表无数据；未证实它们就是当前看板在线源 |

orders还存在带_test、日期后缀等表，本轮仅列元数据，不因表名相似就混入生产统计口径。

## 时间字段

| 字段 | 当前证据 | 查询方式/限制 |
| --- | --- | --- |
| fb_members_login_log.created_at | 全2244条均为10位秒值 | 用秒级范围；UTC+8自然日转换加28800再除86400 |
| fb_members_login_log.created_time | datetime；与秒值+8小时相差0—3秒 | 1962条相同，282条晚1—3秒；不可未经验证替换created_at，日界线可能不同 |
| fb_members.created_at | 最近最多1000条样本为13位毫秒 | 用毫秒范围；不据此类推全部时间字段 |
| fb_deposits.created_at / paid_at | 最近最多1000条样本为毫秒，paid_at含0 | 0不是有效到账时间；人工补单还需以状态/会员字段核实，不强制假设paid_at必填 |
| fb_withdraws.created_at | 最近最多1000条样本为毫秒 | created_at不自动等于提现完成归属时间 |
| tbl_game_record.settle_time | FAT最近最多1000条样本为毫秒 | 结算日期与下注/创建日期不同；先查结算状态 |

会话时区为SYSTEM、系统显示CST；本轮用与时间戳相对的日期运算显式确认UTC+8，不单凭CST缩写判断。登录表分区边界为13位毫秒量级，实际created_at为10位秒；元数据行数集中首分区。这是结构/值量级异常观察，不能按分区名字判断日志日期或保留范围，也未改分区。

## 登录人数

用户明确来源为fb_members_login_log。本轮候选取数：`prefix='fat' AND state=1`，按UTC+8日分组后`COUNT(DISTINCT uid)`。与09-28保存的07-01—09-27报表相比86天一致；07-01—03报表7/6/5，当前源表无记录，现存最早07-04。数据保留/历史迁移原因未证实，不将源表缺记录直接判为报表错误。

字段注释：state为1成功/0失败，is_reg为1注册/0非注册，is_first_today为1当日首次/0非首次，prefix为环境。实际包含密码、OTP、fb登录与注册、代理密码登陆。不要未经规则依据排除注册或代理：这些过滤会增加对账差异。亦不能用SUM(is_first_today)代替UID去重。与当前会员表INNER JOIN可能排除历史或代理标识，不能为了“只算会员”悄悄改变统计范围。

可复查的示例（2026-09-25 UTC+8；秒级，不选取个人明细）：

```sql
START TRANSACTION READ ONLY;
SELECT COUNT(*) AS success_events, COUNT(DISTINCT uid) AS login_users
FROM fat.fb_members_login_log
WHERE prefix = 'fat' AND state = 1
  AND created_at >= 1790265600 AND created_at < 1790352000;
ROLLBACK;
```

上述是与历史API吻合的实现观察，尚未从后端代码证实线上实际SQL；也没有失败日志样本验证state过滤的差异。

## 充值与注单状态

gt=0不是单一业务场景，当前全表状态/来源分布及次数核查见[09-29专项说明](gt-zero-20260929.md)。默认待处理、多次成功充值、系统生成及未归因历史记录均存在，不能一概当首充或第四次以后。

- deposits.gt注释：0其他、1首充、2二充、3三充。[GCash实测](../../requirements/history/archived-20261005/ISOP-2092/verification-20260929-gcash.md)提单PENDING均gt=0，完成首笔变1、二笔变2；老账号第42次完成仍0。2092用户最新核定复充金额取gt>1，并结合Completed、会员提交及首充当天判断；gt=0和gt=1均排除，见[Q-02](../../requirements/history/archived-20261005/ISOP-2092/questions.md#q-02)。三充3仅注释，本轮未新增三充实测。
- deposits.save_ty：1会员提交、2系统自动生成。paid_amount四位，amount八位；“金额都只存四位”不成立。枚举不代替具体报表纳入范围。
- 主/体育注单state：0未结算、1已结算、2会员取消、3无效（字段注释）。bet_amount/net_amount为钱包币种，net_amount注释为玩家输赢，不得不区分视角直接当公司GGR。
- 2092派彩按用户09-29明确口径，用bet_amount + net_amount回推，覆盖全部类型，再按需求计JP且核实不重复。总投注/有效投注仅bet_type 1/3是2092规则，不能套到派彩。不把源码派彩缺独立字段继续当阻塞，09-29已按新口径对账，4日差额登记TEST-3203；源加工根因仍待定位。

2092充值金额最新字段依据：用户确认取amount，Completed会员提交等筛选不变；这是报表定义，不表示amount与paid_amount在数据库里恒等。07-03分别1600/1360，报表1600正确。详见[Q-05](../../requirements/history/archived-20261005/ISOP-2092/questions.md#q-05)。

## 2092总派彩两表取数补充（09-29）

按用户提供的新取数逻辑：UTC+8的settle_time、state=1、prefix='fat'、site_id=0；orders.tbl_game_record仅取game_class<>'4'，orders.tbl_game_record_sport仅取game_class='4'，不限制bet_type。分别SUM(bet_amount+net_amount+jp_winning)后相加；无记录的SUM按0处理。该范围用于本次总派彩对账，不自动扩大为总投注/GGR等其他指标的已验证口径。

8月31日及月报实时核对完全一致，总額585207.335；该月无符合条件的体育专表记录。09-16体育来源替换后对平，其他三个已核9月日期仍有差额。此前主表89日差额属于旧取数口径，后续以[补核记录](../../requirements/history/archived-20261005/ISOP-2092/verification-20260929-payout-review.md)为准，不能直接将旧对账推广为当前结论。
