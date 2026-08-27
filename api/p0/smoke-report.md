# P0 API Smoke Report

生成时间：`2026-08-26T14:27:34.471197+08:00`

## 执行范围

- 环境：FAT
- 用例来源：`api/p0/test-cases.csv`
- 请求编码：CBOR
- 响应解码：CBOR/JSON
- TLS：测试环境临时使用 `--insecure`

## 结果概览

| 指标 | 数量 |
| --- | --- |
| 登录请求 | 4 |
| P0 用例 | 30 |
| 断言通过 | 30 |
| 断言失败 | 0 |

## 领域分布

| 领域 | 用例数 |
| --- | --- |
| finance | 12 |
| game | 7 |
| member | 6 |
| kyc | 4 |
| admin | 1 |

## 失败用例

无。

## 用例明细

| 用例ID | 流程阶段 | 领域 | 用例 | HTTP | 业务状态 | 断言 | 耗时 | 摘要 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-001 | KYC | kyc | 查询会员 KYC 详情 | 200 | True | PASS | 135ms | keys: uid, created_at, updated_at, country_code, phone, first_name, middle_name, last_name |
| TC-002 | KYC | kyc | 查询 eKYC 配置 | 200 | True | PASS | 146ms | keys: state, signature_id |
| TC-003 | 充值 | finance | 获取充值/提现渠道列表 | 200 | True | PASS | 158ms | list[3] |
| TC-004 | 充值相关数据检查 | finance | 查询会员充值记录 | 200 | True | PASS | 138ms | keys: d, t, s |
| TC-005 | 投注 | game | 查询历史游戏 | 200 | True | PASS | 132ms | None |
| TC-006 | 投注 | game | 查询最近游戏 | 200 | True | PASS | 152ms | keys: d, t, s |
| TC-007 | 投注 | game | 查询推荐游戏 | 200 | True | PASS | 129ms | keys: d, t, s |
| TC-008 | 投注 | game | 查询新版游戏列表组合 | 200 | True | PASS | 137ms | keys: d, t, s |
| TC-009 | 投注 | game | 查询新版首页游戏聚合 | 200 | True | PASS | 266ms | keys: banners, top, middle, bottom, loading, logo, singup, media |
| TC-010 | 派彩/投注相关数据检查 | game | 查询会员游戏记录 | 200 | True | PASS | 317ms | keys: t, wt, bt, d |
| TC-011 | 提现 | finance | 查询提款账户列表 | 200 | True | PASS | 139ms | list[2] |
| TC-012 | 提现 | finance | 查询客户端银行列表 | 200 | True | PASS | 144ms | keys: d, t, s |
| TC-013 | 提现 | finance | 查询提现 tab 配置 | 200 | True | PASS | 144ms | list[3] |
| TC-014 | 提现相关数据检查 | finance | 查询会员提现记录 | 200 | True | PASS | 135ms | keys: d, t, s |
| TC-015 | 以上相关数据检查 | finance | 查询会员账变记录 | 200 | True | PASS | 137ms | keys: t, s, data |
| TC-016 | 以上相关数据检查 | finance | 查询账变类型字典 | 200 | True | PASS | 137ms | list[8] |
| TC-017 | 以上相关数据检查 | finance | 查询会员钱包 | 200 | True | PASS | 132ms | keys: uid, balance, withdrawable, locked |
| TC-018 | 以上相关数据检查 | finance | 查询代币明细 | 200 | True | PASS | 154ms | keys: d, t, s, last_id |
| TC-019 | 以上相关数据检查 | game | 查询游戏收藏列表 | 200 | True | PASS | 133ms | keys: d, t, s |
| TC-020 | 以上相关数据检查 | member | 查询代理审核结果 | 200 | True | PASS | 135ms | keys:  |
| TC-021 | 以上相关数据检查 | member | 查询代理申请问题列表 | 200 | True | PASS | 311ms | keys: problem1, problem2, problem3, problem4 |
| TC-022 | 以上相关数据检查 | member | 查询会员基础信息 | 200 | True | PASS | 136ms | keys: uid, username, email, email_check_state, country_code, phone, phone_check_state, avatar |
| TC-023 | 以上相关数据检查 | member | 查询会员 VIP 等级详情 | 200 | True | PASS | 136ms | keys: uid, username, level, ty, upgrade_xp, cur_upgrade_xp, rem_upgrade_xp, keep_xp_days |
| TC-024 | 以上相关数据检查 | member | 查询新版 VIP 配置 | 200 | True | PASS | 192ms | keys: 19, 17, 13, 20, 5, 1, 9, 3 |
| TC-025 | 以上相关数据检查 | member | 查询新版 VIP 签到配置 | 200 | True | PASS | 174ms | keys: level, ty, mk_lmt, cl_mk_cd, d6_ci_amount, d7ci_amount, d16_ci_amount, d17ci_amount |
| TC-026 | 后台报表展示和审批 | admin | 后台查询当前登录用户详情 | 200 | True | PASS | 159ms | keys: id, email, avatar, nickname, login_password, last_login_ip, last_login_time, roles |
| TC-027 | 后台报表展示和审批 | finance | 后台查询银行卡列表 | 200 | True | PASS | 180ms | keys: d, t, s |
| TC-028 | 后台报表展示和审批 | finance | 后台查询账变类型 | 200 | True | PASS | 157ms | list[16] |
| TC-029 | 后台报表展示和审批 | kyc | 后台查询 KYC 待审批数量 | 200 | True | PASS | 158ms | 42 |
| TC-030 | 后台报表展示和审批 | kyc | 后台查询 eKYC 配置 | 200 | True | PASS | 149ms | keys: id, ekyc, auto_review |


## 已知替代关系

| 老接口 | 状态 | 替代接口 |
| --- | --- | --- |
| `GET /member/game/list` | HTTP 200 但业务 `status=false` | `GET /member/v2/index`、`GET /member/game/listRw`、`GET /member/game/list/recommend` |
| `GET /member/vip` | HTTP 200 但业务失败 | `GET /promo/vip/config`、`GET /promo/vip/sign/in/config` |

