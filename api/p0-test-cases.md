# P0 API 测试用例

来源：`api/p0-interface-shortlist.csv`

全量 CSV：`/Users/rayleigh/qa-automation/api/p0-test-cases.csv`

## 总览

| 指标 | 数量 |
| --- | --- |
| P0 可执行用例 | 18 |
| safe_smoke | 18 |

## 领域分布

| 领域 | 数量 |
| --- | --- |
| finance | 7 |
| game | 6 |
| member | 4 |
| kyc | 1 |

## 用例清单

| 用例ID | 流程阶段 | 领域 | 用例 | 方法 | Clean URL | 断言 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-001 | KYC | kyc | 查询会员 KYC 详情 | GET | {{api_url}}/member/kyc/detail | status_true,data_object,keys:data.uid\|data.phone |
| TC-002 | 充值 | finance | 获取充值/提现渠道列表 | GET | {{api_url}}/finance/channel/list?mode=2&source=huawei | status_true,data_list |
| TC-003 | 充值相关数据检查 | finance | 查询会员充值记录 | GET | {{api_url}}/finance/deposit/list?status=PENDING&time_flag=0&page=1&page_size=10 | status_true,data_object,keys:data.d\|data.t\|data.s |
| TC-004 | 投注 | game | 查询历史游戏 | GET | {{api_url}}/member/game/list/history | status_true |
| TC-005 | 投注 | game | 查询最近游戏 | GET | {{api_url}}/member/game/list/recent?page=1&page_size=10 | status_true,data_object,keys:data.d\|data.t\|data.s |
| TC-006 | 投注 | game | 查询推荐游戏 | GET | {{api_url}}/member/game/list/recommend | status_true,data_object,keys:data.d\|data.t\|data.s |
| TC-007 | 投注 | game | 查询新版游戏列表组合 | GET | {{api_url}}/member/game/listRw?page=1&page_size=10&venues=op&sort=4 | status_true,data_object,keys:data.d\|data.t\|data.s |
| TC-008 | 投注 | game | 查询新版首页游戏聚合 | GET | {{api_url}}/member/v2/index | status_true,data_object,keys:data.banners |
| TC-009 | 派彩/投注相关数据检查 | game | 查询会员游戏记录 | GET | {{api_url}}/member/game/bet/list?page=1&page_size=10&time_flag=30&status=1 | status_true,data_object,keys:data.d\|data.t |
| TC-010 | 提现 | finance | 查询提现 tab 配置 | GET | {{api_url}}/finance/payment/tab/list | status_true,data_list |
| TC-011 | 提现相关数据检查 | finance | 查询会员提现记录 | GET | {{api_url}}/finance/withdraw/list?time_flag=0&page=1&page_size=10 | status_true,data_object,keys:data.d\|data.t\|data.s |
| TC-012 | 以上相关数据检查 | finance | 查询会员账变记录 | GET | {{api_url}}/finance/transaction/list?time_flag=15&page=1&page_size=20 | status_true,data_object,keys:data.data\|data.t\|data.s |
| TC-013 | 以上相关数据检查 | finance | 查询账变类型字典 | GET | {{api_url}}/finance/transaction/types | status_true,data_list |
| TC-014 | 以上相关数据检查 | finance | 查询会员钱包 | GET | {{api_url}}/finance/wallet | status_true,data_object,keys:data.uid\|data.balance\|data.withdrawable\|data.locked |
| TC-015 | 以上相关数据检查 | member | 查询会员基础信息 | GET | {{api_url}}/member/detail | status_true,data_object,keys:data.uid\|data.username\|data.phone |
| TC-016 | 以上相关数据检查 | member | 查询会员 VIP 等级详情 | GET | {{api_url}}/member/vip/level/detail | status_true,data_object,keys:data.uid\|data.level |
| TC-017 | 以上相关数据检查 | member | 查询新版 VIP 配置 | GET | {{api_url}}/promo/vip/config | status_true,data_object |
| TC-018 | 以上相关数据检查 | member | 查询新版 VIP 签到配置 | GET | {{api_url}}/promo/vip/sign/in/config | status_true,data_object,keys:data.level\|data.ty |
