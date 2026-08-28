# Database Debug

## 用途

记录测试环境数据库只读排查口径。数据库只用于辅助理解字段、状态枚举、账号前置和落库一致性，不作为默认 API/UI 门禁依赖。

不要把数据库地址、账号、密码提交到仓库；本文件只记录字段含义和排查结论。

## 当前主库判断

当前 FAT 主业务库优先看 `fat`。

核心表：

| 表 | 用途 |
| --- | --- |
| `fat.fb_members` | 会员主表，包含手机号、账号状态、KYC 主状态、累计充值提现 |
| `fat.fb_members_kyc` | KYC 明细表，包含实名信息、审核状态、OCR/eKYC 相关字段 |
| `fat.fb_members_balance` | 会员钱包旧余额口径 |
| `fat.fb_members_balance_new` | 会员钱包新余额/合规余额口径 |
| `fat.fb_members_turnover` | 活动、充值、后台上分等产生的流水限制 |
| `fat.fb_deposits` | 充值订单 |
| `fat.fb_withdraws` | 提现订单 |
| `fat.fb_balance_transaction` | 钱包账变 |
| `fat.fb_bet_transaction_map` | 投注记录和账变映射 |
| `fat.fb_member_ekyc_config` | eKYC 配置 |
| `fat.fb_withdraws_limit_record` | 提现限制记录 |

## 关键状态字段

`fat.fb_members.kyc_status`：

- `1`：Basic Account
- `2`：Basic KYC
- `3`：Under Review
- `4`：Reject KYC
- `5`：Fully KYC
- `6`：Frozen
- `7`：Block
- `8`：Test Account

实际 FAT 数据里当前常见值为 `0`、`2`、`3`、`5`。其中 `5` 可视为已通过 KYC。

`fat.fb_members_kyc.kyc_status`：

- 字段注释：`0 pending`、`2 待审`、`3 驳回`、`5 通过`
- 同表 `status` 是文本状态，常见值包括 `Pending`、`Under Review`、`Resubmit Required`、`approved`。

`fat.fb_withdraws`：

- `status`：提现业务状态，例如 `under_review`、`paying`、`completed`、`canceled`、`timeout`
- `approval`：审核状态，字段注释为 `0 待审核 1审核失败 2审核成功 3 自动审核`
- `payout`：出款状态，字段注释为 `0 待出款 1出款中 2出款成功 3 出款失败`

`fat.fb_members_turnover`：

- `ty`：流水类型，字段注释为 `1 后台上分 2 活动彩金 3 存款 4 风控调整 6 免费旋转`
- `state`：流水状态，字段注释为 `1 未完成 2 已完成 3 清零`
- `turnover - finished`：剩余流水
- `locked`：锁定金额

## 当前自动化账号观察

当前客户端自动化账号：

- `fb_members.kyc_status = 5`，说明 KYC 已通过。
- `fb_members.state = 0`，会员状态正常。
- 存在多条 `fb_members_turnover.state = 1` 的未完成流水。
- 未完成流水合计和锁定金额一致，当前观察值为 `20633.24`。
- 这解释了提现申请没有生成待审单的主要前置风险：不是 KYC 未通过，而是账号存在活动/充值流水限制。

因此，P0 提现正向自动化需要更换为无未完成流水限制的专用账号，或先通过可控方式完成/清理流水。

后续接口探针已确认：

- 只要账号已 KYC、无未完成流水、钱包 `locked=0`、有可用提款账户，提现创建接口可以返回 `status=true`。
- 提现金额需要避开低于免审阈值 `500` 的自动出款路径；当前正例使用 `1000`。
- 充值补单会新增未完成流水和锁定金额，因此不适合在同一个账号上紧接着验证提现正例。

## 推荐只读排查 SQL

按手机号确认会员主状态：

```sql
SELECT uid, username, tester, state, kyc_status, deposit_total, withdraw_total
FROM fat.fb_members
WHERE phone = '<client phone>';
```

确认钱包余额口径：

```sql
SELECT b.uid, b.balance, b.available, b.withdrawable, b.total_balance
FROM fat.fb_members_balance b
JOIN fat.fb_members m ON m.uid = b.uid
WHERE m.phone = '<client phone>';
```

确认未完成流水：

```sql
SELECT
  SUM(CASE WHEN t.state = 1 THEN t.turnover - t.finished ELSE 0 END) AS unfinished_turnover,
  SUM(CASE WHEN t.state = 1 THEN t.locked ELSE 0 END) AS active_locked,
  COUNT(CASE WHEN t.state = 1 THEN 1 END) AS active_turnover_count
FROM fat.fb_members_turnover t
JOIN fat.fb_members m ON m.uid = t.uid
WHERE m.phone = '<client phone>';
```
