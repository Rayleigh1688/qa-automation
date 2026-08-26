# P0 API Smoke Report

生成时间：`2026-08-26T10:53:37.989134+08:00`

## 执行范围

- 环境：FAT
- 用例来源：`api/p0-test-cases.csv`
- 请求编码：CBOR
- 响应解码：CBOR/JSON
- TLS：测试环境临时使用 `--insecure`

## 结果概览

| 指标 | 数量 |
| --- | --- |
| 登录请求 | 2 |
| P0 用例 | 18 |
| 断言通过 | 18 |
| 断言失败 | 0 |

## 领域分布

| 领域 | 用例数 |
| --- | --- |
| finance | 7 |
| game | 6 |
| member | 4 |
| kyc | 1 |

## 失败用例

无。

## 用例明细

| 用例ID | 流程阶段 | 领域 | 用例 | HTTP | 业务状态 | 断言 | 耗时 | 摘要 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-001 | KYC | kyc | 查询会员 KYC 详情 | 200 | True | PASS | 144ms | keys: uid, created_at, updated_at, country_code, phone, first_name, middle_name, last_name |
| TC-002 | 充值 | finance | 获取充值/提现渠道列表 | 200 | True | PASS | 162ms | list[3] |
| TC-003 | 充值相关数据检查 | finance | 查询会员充值记录 | 200 | True | PASS | 164ms | keys: d, t, s |
| TC-004 | 投注 | game | 查询历史游戏 | 200 | True | PASS | 166ms | None |
| TC-005 | 投注 | game | 查询最近游戏 | 200 | True | PASS | 168ms | keys: d, t, s |
| TC-006 | 投注 | game | 查询推荐游戏 | 200 | True | PASS | 184ms | keys: d, t, s |
| TC-007 | 投注 | game | 查询新版游戏列表组合 | 200 | True | PASS | 169ms | keys: d, t, s |
| TC-008 | 投注 | game | 查询新版首页游戏聚合 | 200 | True | PASS | 310ms | keys: banners, top, middle, bottom, loading, logo, singup, media |
| TC-009 | 派彩/投注相关数据检查 | game | 查询会员游戏记录 | 200 | True | PASS | 167ms | keys: t, wt, bt, d |
| TC-010 | 提现 | finance | 查询提现 tab 配置 | 200 | True | PASS | 158ms | list[3] |
| TC-011 | 提现相关数据检查 | finance | 查询会员提现记录 | 200 | True | PASS | 167ms | keys: d, t, s |
| TC-012 | 以上相关数据检查 | finance | 查询会员账变记录 | 200 | True | PASS | 176ms | keys: t, s, data |
| TC-013 | 以上相关数据检查 | finance | 查询账变类型字典 | 200 | True | PASS | 170ms | list[8] |
| TC-014 | 以上相关数据检查 | finance | 查询会员钱包 | 200 | True | PASS | 344ms | keys: uid, balance, withdrawable, locked |
| TC-015 | 以上相关数据检查 | member | 查询会员基础信息 | 200 | True | PASS | 175ms | keys: uid, username, email, email_check_state, country_code, phone, phone_check_state, avatar |
| TC-016 | 以上相关数据检查 | member | 查询会员 VIP 等级详情 | 200 | True | PASS | 161ms | keys: uid, username, level, ty, upgrade_xp, cur_upgrade_xp, rem_upgrade_xp, keep_xp_days |
| TC-017 | 以上相关数据检查 | member | 查询新版 VIP 配置 | 200 | True | PASS | 234ms | keys: 7, 12, 6, 19, 20, 14, 15, 21 |
| TC-018 | 以上相关数据检查 | member | 查询新版 VIP 签到配置 | 200 | True | PASS | 181ms | keys: level, ty, mk_lmt, cl_mk_cd, d6_ci_amount, d7ci_amount, d16_ci_amount, d17ci_amount |

## 已知替代关系

| 老接口 | 状态 | 替代接口 |
| --- | --- | --- |
| `GET /member/game/list` | HTTP 200 但业务 `status=false` | `GET /member/v2/index`、`GET /member/game/listRw`、`GET /member/game/list/recommend` |
| `GET /member/vip` | HTTP 200 但业务失败 | `GET /promo/vip/config`、`GET /promo/vip/sign/in/config` |
