# P0 API 测试用例

来源：`api/p0/interface-shortlist.csv`、`api/runbooks/ADMIN.md`、前端真实网络请求

全量 CSV：`/Users/rayleigh/qa-automation/api/p0/test-cases.csv`

## 总览

| 指标 | 数量 |
| --- | --- |
| P0 可执行用例 | 30 |
| safe_smoke | 30 |

## 领域分布

| 领域 | 数量 |
| --- | --- |
| finance | 12 |
| game | 7 |
| member | 6 |
| kyc | 4 |
| admin | 1 |

## 用例清单

| 用例ID | 流程阶段 | 领域 | 用例 | 方法 | Clean URL | 断言 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-001 | KYC | kyc | 查询会员 KYC 详情 | GET | {{api_url}}/member/kyc/detail | status_true,data_object,keys:data.uid\|data.phone |
| TC-002 | KYC | kyc | 查询 eKYC 配置 | GET | {{api_url}}/member/kyc/ekyc/info | status_true,data_object,keys:data.state\|data.signature_id |
| TC-003 | 充值 | finance | 获取充值/提现渠道列表 | GET | {{api_url}}/finance/channel/list?mode=2&source=huawei | status_true,data_list |
| TC-004 | 充值相关数据检查 | finance | 查询会员充值记录 | GET | {{api_url}}/finance/deposit/list?status=PENDING&time_flag=0&page=1&page_size=10 | status_true,data_object,keys:data.d\|data.t\|data.s |
| TC-005 | 投注 | game | 查询历史游戏 | GET | {{api_url}}/member/game/list/history | status_true |
| TC-006 | 投注 | game | 查询最近游戏 | GET | {{api_url}}/member/game/list/recent?page=1&page_size=10 | status_true,data_object,keys:data.d\|data.t\|data.s |
| TC-007 | 投注 | game | 查询推荐游戏 | GET | {{api_url}}/member/game/list/recommend | status_true,data_object,keys:data.d\|data.t\|data.s |
| TC-008 | 投注 | game | 查询新版游戏列表组合 | GET | {{api_url}}/member/game/listRw?page=1&page_size=10&venues=op&sort=4 | status_true,data_object,keys:data.d\|data.t\|data.s |
| TC-009 | 投注 | game | 查询新版首页游戏聚合 | GET | {{api_url}}/member/v2/index | status_true,data_object,keys:data.banners |
| TC-010 | 派彩/投注相关数据检查 | game | 查询会员游戏记录 | GET | {{api_url}}/member/game/bet/list?page=1&page_size=10&time_flag=30&status=1 | status_true,data_object,keys:data.d\|data.t |
| TC-011 | 提现 | finance | 查询提款账户列表 | GET | {{api_url}}/finance/account/list | status_true,data_list |
| TC-012 | 提现 | finance | 查询客户端银行列表 | GET | {{api_url}}/finance/payment/bank/list?page=2&page_size=10 | status_true,data_object,keys:data.d\|data.t\|data.s |
| TC-013 | 提现 | finance | 查询提现 tab 配置 | GET | {{api_url}}/finance/payment/tab/list | status_true,data_list |
| TC-014 | 提现相关数据检查 | finance | 查询会员提现记录 | GET | {{api_url}}/finance/withdraw/list?time_flag=0&page=1&page_size=10 | status_true,data_object,keys:data.d\|data.t\|data.s |
| TC-015 | 以上相关数据检查 | finance | 查询会员账变记录 | GET | {{api_url}}/finance/transaction/list?time_flag=15&page=1&page_size=20 | status_true,data_object,keys:data.data\|data.t\|data.s |
| TC-016 | 以上相关数据检查 | finance | 查询账变类型字典 | GET | {{api_url}}/finance/transaction/types | status_true,data_list |
| TC-017 | 以上相关数据检查 | finance | 查询会员钱包 | GET | {{api_url}}/finance/wallet | status_true,data_object,keys:data.uid\|data.balance\|data.withdrawable\|data.locked |
| TC-018 | 以上相关数据检查 | finance | 查询代币明细 | GET | {{api_url}}/promo/task/transaction | status_true,data_object,keys:data.d\|data.t\|data.s |
| TC-019 | 以上相关数据检查 | game | 查询游戏收藏列表 | GET | {{api_url}}/member/fav/list?page=1&page_size=10 | status_true,data_object,keys:data.d\|data.t\|data.s |
| TC-020 | 以上相关数据检查 | member | 查询代理审核结果 | GET | {{api_url}}/member/agency/audit/results | status_true,data_object |
| TC-021 | 以上相关数据检查 | member | 查询代理申请问题列表 | GET | {{api_url}}/member/agency/problem/list | status_true,data_object,keys:data.problem1\|data.problem2\|data.problem3\|data.problem4 |
| TC-022 | 以上相关数据检查 | member | 查询会员基础信息 | GET | {{api_url}}/member/detail | status_true,data_object,keys:data.uid\|data.username\|data.phone |
| TC-023 | 以上相关数据检查 | member | 查询会员 VIP 等级详情 | GET | {{api_url}}/member/vip/level/detail | status_true,data_object,keys:data.uid\|data.level |
| TC-024 | 以上相关数据检查 | member | 查询新版 VIP 配置 | GET | {{api_url}}/promo/vip/config | status_true,data_object |
| TC-025 | 以上相关数据检查 | member | 查询新版 VIP 签到配置 | GET | {{api_url}}/promo/vip/sign/in/config | status_true,data_object,keys:data.level\|data.ty |
| TC-026 | 后台报表展示和审批 | admin | 后台查询当前登录用户详情 | GET | {{admin_url}}/admin/me/detail | status_true,data_object |
| TC-027 | 后台报表展示和审批 | finance | 后台查询银行卡列表 | GET | {{admin_url}}/admin/finance/payment/bank/list | status_true,data_object,keys:data.d\|data.t\|data.s |
| TC-028 | 后台报表展示和审批 | finance | 后台查询账变类型 | GET | {{admin_url}}/admin/finance/transaction/types | status_true,data_list |
| TC-029 | 后台报表展示和审批 | kyc | 后台查询 KYC 待审批数量 | GET | {{admin_url}}/admin/kyc/pending/count | status_true |
| TC-030 | 后台报表展示和审批 | kyc | 后台查询 eKYC 配置 | GET | {{admin_url}}/admin/kyc/config/info | status_true,data_object |
