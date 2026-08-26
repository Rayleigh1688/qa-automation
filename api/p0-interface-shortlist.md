# P0 接口候选清单

来源：`api/interface-inventory.csv`

全量清单：`/Users/rayleigh/qa-automation/api/p0-interface-shortlist.csv`

## 总览

| 指标 | 数量 |
| --- | --- |
| P0 shortlist 接口 | 166 |
| 可直接冒烟 safe_smoke | 18 |
| 需要 token token_required | 37 |
| 需要人工复核 manual_review | 106 |
| 仅复核 review_only | 5 |

## 领域分布

| 领域 | 数量 |
| --- | --- |
| finance | 75 |
| kyc | 42 |
| auth | 26 |
| member | 13 |
| game | 10 |

## 可先冒烟的 GET 接口

这些接口优先用于连通性和基础响应结构验证。真正进入门禁前仍需确认是否需要 token、设备号、语言或特殊 header。

| 优先级 | 领域 | 方法 | Clean URL | 来源 |
| --- | --- | --- | --- | --- |
| P0-027 | finance | GET | {{api_url}}/finance/channel/list?mode=2&source=huawei | 前台/财务/获取支付通道列表-wesley.bru |
| P0-028 | finance | GET | {{api_url}}/finance/deposit/list?status=PENDING&time_flag=0&page=1&page_size=10 | 前台/财务/充值记录-wesley.bru |
| P0-029 | finance | GET | {{api_url}}/finance/payment/tab/list | 前台/财务/提现tab.bru |
| P0-030 | finance | GET | {{api_url}}/finance/transaction/list?time_flag=15&page=1&page_size=20 | 前台/财务/获取交易记录- wesley-alex.bru |
| P0-031 | finance | GET | {{api_url}}/finance/transaction/types | 前台/财务/账变字典.bru |
| P0-032 | finance | GET | {{api_url}}/finance/wallet | 前台/财务/会员钱包-wesley.bru |
| P0-033 | finance | GET | {{api_url}}/finance/withdraw/list?time_flag=0&page=1&page_size=10 | 前台/财务/提现记录-wesley.bru |
| P0-102 | game | GET | {{api_url}}/member/game/bet/list?page=1&page_size=10&time_flag=30&status=1 | 前台/游戏/游戏记录-wesley.bru |
| P0-103 | game | GET | {{api_url}}/member/game/list/history | 前台/游戏/历史游戏列表-light.bru |
| P0-104 | game | GET | {{api_url}}/member/game/list/recent?page=1&page_size=10 | 前台/游戏/最近游戏-benjie.bru |
| P0-105 | game | GET | {{api_url}}/member/game/list/recommend | 前台/游戏/推荐列表-benjie.bru |
| P0-106 | game | GET | {{api_url}}/member/game/listRw?page=1&page_size=10&venues=op&sort=4 | 前台/游戏/游戏查询语句组合-benjie.bru |
| P0-107 | game | GET | {{api_url}}/member/v2/index | 前台/游戏/首页缓存v2-owen.bru |
| P0-112 | kyc | GET | {{api_url}}/member/kyc/detail | 前台/kyc/获取 kyc 详情 -- double-cold.bru |
| P0-154 | member | GET | {{api_url}}/member/detail | 前台/会员信息/获取会员信息-seven-aliang(20260424).bru |
| P0-155 | member | GET | {{api_url}}/member/vip/level/detail | 前台/VIP/会员vip等级详情.bru |
| P0-156 | member | GET | {{api_url}}/promo/vip/config | 活动/Vip/vip配置.bru |
| P0-157 | member | GET | {{api_url}}/promo/vip/sign/in/config | 活动/Vip/签到配置.bru |

## P0 shortlist

| 优先级 | 策略 | 领域 | 方法 | Clean URL | 标记 | 来源 |
| --- | --- | --- | --- | --- | --- | --- |
| P0-001 | token_required | auth | GET | {{api_url}}/member/facebook_link |  | 前台/会员信息/facebook oauth链接-ducky.bru |
| P0-002 | token_required | auth | GET | {{api_url}}/member/google_link |  | 前台/会员信息/google oauth链接-ducky.bru |
| P0-003 | token_required | auth | GET | {{api_url}}/member/logout |  | 前台/会员登陆注册验证/退出登陆-seven.bru |
| P0-004 | token_required | auth | GET | {{api_url}}/member/refresh/token |  | 前台/会员登陆注册验证/刷新token-seven.bru |
| P0-005 | manual_review | auth | POST | {{admin_url}}/admin/finance/lazada/send/sms |  | 后台/财务管理/lazada订单/lazada-重新发货-owen.bru |
| P0-006 | manual_review | auth | POST | {{api_url}}/finance/lazadaminiapp/login |  | 前台/lazada mini/登陆-owen.bru |
| P0-007 | manual_review | auth | POST | {{api_url}}/member/auth/mail |  | 前台/会员信息/邮箱验证码验证-ducky.bru |
| P0-008 | manual_review | auth | POST | {{api_url}}/member/auth/sms |  | 前台/会员登陆注册验证/短信验证码前置检查-seven.bru |
| P0-009 | manual_review | auth | POST | {{api_url}}/member/bind/facebook |  | 前台/会员信息/facebook oauth绑定-ducky.bru |
| P0-010 | manual_review | auth | POST | {{api_url}}/member/bind/google |  | 前台/会员信息/google oauth绑定-ducky.bru |
| P0-011 | manual_review | auth | POST | {{api_url}}/member/facebook/login |  | 前台/会员登陆注册验证/facebook oauth登录-ducky.bru |
| P0-012 | manual_review | auth | POST | {{api_url}}/member/fb/login | hardcoded_env | 前台/三方登录/注册接口.bru |
| P0-013 | manual_review | auth | POST | {{api_url}}/member/google/login |  | 前台/会员登陆注册验证/google oauth登录-ducky.bru |
| P0-014 | manual_review | auth | POST | {{api_url}}/member/login |  | 前台/会员登陆注册验证/密码登陆-seven.bru |
| P0-015 | manual_review | auth | POST | {{api_url}}/member/otp/login |  | 前台/会员登陆注册验证/otp登陆-seven.bru |
| P0-016 | manual_review | auth | POST | {{api_url}}/member/otp/login/v2 | url_v2 | 前台/会员登陆注册验证/otp登陆V2-seven.bru |
| P0-017 | manual_review | auth | POST | {{api_url}}/member/password/update |  | 前台/会员信息/密码修改-seven.bru |
| P0-018 | manual_review | auth | POST | {{api_url}}/member/register | hardcoded_env | 前台/会员登陆注册验证/注册.bru |
| P0-019 | manual_review | auth | POST | {{api_url}}/member/retrieve/password |  | 前台/会员登陆注册验证/重置密码-seven.bru |
| P0-020 | manual_review | auth | POST | {{api_url}}/member/retrieve/passwordbyemail |  | 前台/会员信息/通过邮箱修改密码-ducky.bru |
| P0-021 | manual_review | auth | POST | {{api_url}}/member/sms |  | 前台/会员登陆注册验证/短信发送-seven.bru |
| P0-022 | manual_review | auth | POST | {{api_url}}/member/v2/login | url_v2 | 前台/会员登陆注册验证/密码登陆v2-ducky.bru |
| P0-023 | manual_review | auth | POST | {{api_url}}/member/wallet/checkpassword |  | 前台/会员信息/校验钱包密码-ducky.bru |
| P0-024 | manual_review | auth | POST | {{api_url}}/member/wallet/password |  | 前台/会员信息/钱包密码设置-ducky.bru |
| P0-025 | manual_review | auth | POST | {{api_url}}/member/wallet/password/update |  | 前台/会员信息/设置新钱包密码-ducky.bru |
| P0-026 | review_only | auth | POST | {{api_url}}/member/auth/password | old_or_copy | 前台/会员登陆注册验证/旧密码前置验证-seven.bru |
| P0-027 | safe_smoke | finance | GET | {{api_url}}/finance/channel/list?mode=2&source=huawei |  | 前台/财务/获取支付通道列表-wesley.bru |
| P0-028 | safe_smoke | finance | GET | {{api_url}}/finance/deposit/list?status=PENDING&time_flag=0&page=1&page_size=10 |  | 前台/财务/充值记录-wesley.bru |
| P0-029 | safe_smoke | finance | GET | {{api_url}}/finance/payment/tab/list | hardcoded_env | 前台/财务/提现tab.bru |
| P0-030 | safe_smoke | finance | GET | {{api_url}}/finance/transaction/list?time_flag=15&page=1&page_size=20 |  | 前台/财务/获取交易记录- wesley-alex.bru |
| P0-031 | safe_smoke | finance | GET | {{api_url}}/finance/transaction/types |  | 前台/财务/账变字典.bru |
| P0-032 | safe_smoke | finance | GET | {{api_url}}/finance/wallet |  | 前台/财务/会员钱包-wesley.bru |
| P0-033 | safe_smoke | finance | GET | {{api_url}}/finance/withdraw/list?time_flag=0&page=1&page_size=10 |  | 前台/财务/提现记录-wesley.bru |
| P0-034 | token_required | finance | GET | {{admin_url}}/admin/finance/payment/bank/list | hardcoded_env | 后台/财务管理/银行卡/银行卡列表.bru |
| P0-035 | token_required | finance | GET | {{admin_url}}/admin/finance/payment/channel/list?page=1&page_size=10&name&state=1&payment_name=paycools&name |  | 后台/财务管理/支付渠道/支付渠道通道列表.bru |
| P0-036 | token_required | finance | GET | {{admin_url}}/admin/finance/payment/list?page=1&page_size=10&name=paycools&state=1&id |  | 后台/财务管理/支付渠道/x-支付渠道列表-cold.bru |
| P0-037 | token_required | finance | GET | {{admin_url}}/admin/finance/payment/platform/list?page=1&page_size=10&mode=deposit | hardcoded_env | 后台/财务管理/支付渠道/支付平台列表.bru |
| P0-038 | token_required | finance | GET | {{admin_url}}/admin/finance/transaction/types |  | 后台/财务管理/会员钱包账变/账变类型- wesley.bru |
| P0-039 | token_required | finance | GET | {{admin_url}}/agency/finance/transaction/types |  | 代理管理后台/财务管理/财务报表/账变类型- wesley.bru |
| P0-040 | token_required | finance | GET | {{admin_url}}/cmpl/finance/deposit/list |  | 合规/财务管理/财务记录/充值记录-wesley.bru |
| P0-041 | token_required | finance | GET | {{admin_url}}/cmpl/finance/withdraw/list |  | 合规/财务管理/财务记录/提现记录-wesley.bru |
| P0-042 | token_required | finance | GET | {{api_url}}/finance/account/list | hardcoded_env | 前台/财务/提款账户列表-wesley.bru |
| P0-043 | token_required | finance | GET | {{api_url}}/finance/channel/product/list?mode=1&pid=1 | hardcoded_env | 前台/财务/获取支付通道商品列表.bru |
| P0-044 | token_required | finance | GET | {{api_url}}/finance/member/buyfeatures | hardcoded_env | 前台/财务/购买免费旋转游戏列表.bru |
| P0-045 | token_required | finance | GET | {{api_url}}/finance/payment/bank/list?page=2&page_size=10 | hardcoded_env | 前台/财务/银行列表.bru |
| P0-046 | token_required | finance | GET | {{api_url}}/promo/task/transaction |  | 前台/任务中心/代币明细-seven.bru |
| P0-047 | manual_review | finance | POST | {{admin_url}}/admin/finance/adjust/list?uid=1&operator_uid=2&action=1,2&page=1&page_size=10&bill_no=&amount_min=1&amount_max=100&phone= |  | 代理管理后台/财务管理/财务报表/系统调整.bru |
| P0-048 | manual_review | finance | POST | {{admin_url}}/admin/finance/deposit/export |  | 后台/财务管理/存款记录/充值记录导出-wesley.bru |
| P0-049 | manual_review | finance | POST | {{admin_url}}/admin/finance/deposit/list |  | 后台/财务管理/存款记录/充值列表-wesley.bru |
| P0-050 | manual_review | finance | GET | {{admin_url}}/admin/finance/deposit/manual/success |  | 后台/风控管理/存-提审核/充值补单-wesley.bru |
| P0-051 | manual_review | finance | GET | {{admin_url}}/admin/finance/deposit/risk/list |  | 后台/风控管理/存-提审核/充值列表-wesley.bru |
| P0-052 | manual_review | finance | POST | {{admin_url}}/admin/finance/deposit/sync?id=110214866785715045 |  | 后台/财务管理/存款记录/充值同步状态-wesley.bru |
| P0-053 | manual_review | finance | POST | {{admin_url}}/admin/finance/lazada/order/list |  | 后台/财务管理/lazada订单/lazada-订单列表-owen.bru |
| P0-054 | manual_review | finance | GET | {{admin_url}}/admin/finance/payment/Delete?id=998 |  | 后台/财务管理/支付渠道/x-删除支付渠道-cold.bru |
| P0-055 | manual_review | finance | POST | {{admin_url}}/admin/finance/payment/bank/enable | hardcoded_env | 后台/财务管理/银行卡/开启关闭按钮.bru |
| P0-056 | manual_review | finance | POST | {{admin_url}}/admin/finance/payment/bank/insert | hardcoded_env | 后台/财务管理/银行卡/银行卡添加.bru |
| P0-057 | manual_review | finance | POST | {{admin_url}}/admin/finance/payment/bank/update | hardcoded_env | 后台/财务管理/银行卡/银行卡编辑.bru |
| P0-058 | manual_review | finance | GET | {{admin_url}}/admin/finance/payment/channel/delete?id=888 |  | 后台/财务管理/支付渠道/删除支付渠道通道.bru |
| P0-059 | manual_review | finance | POST | {{admin_url}}/admin/finance/payment/channel/insert |  | 后台/财务管理/支付渠道/添加支付渠道通道.bru |
| P0-060 | manual_review | finance | POST | {{admin_url}}/admin/finance/payment/channel/update |  | 后台/财务管理/支付渠道/更新支付渠道通道.bru |
| P0-061 | manual_review | finance | GET | {{admin_url}}/admin/finance/payment/deposit/channels |  | 后台/财务管理/存款记录/支付渠道列表-cold.bru |
| P0-062 | manual_review | finance | POST | {{admin_url}}/admin/finance/payment/insert |  | 后台/财务管理/支付渠道/x-添加支付渠道-cold.bru |
| P0-063 | manual_review | finance | POST | {{admin_url}}/admin/finance/payment/platform/enable |  | 后台/财务管理/支付渠道/支付平台开关.bru |
| P0-064 | manual_review | finance | POST | {{admin_url}}/admin/finance/payment/platform/insert |  | 后台/财务管理/支付渠道/添加支付平台.bru |
| P0-065 | manual_review | finance | POST | {{admin_url}}/admin/finance/payment/platform/update |  | 后台/财务管理/支付渠道/更新支付平台.bru |
| P0-066 | manual_review | finance | POST | {{admin_url}}/admin/finance/payment/update |  | 后台/财务管理/支付渠道/x-更新支付渠道-cold.bru |
| P0-067 | manual_review | finance | GET | {{admin_url}}/admin/finance/payment/withdraw/channels |  | 合规/财务管理/财务记录/提现渠道列表-cold.bru |
| P0-068 | manual_review | finance | GET | {{admin_url}}/admin/finance/payment/withdraw/channels |  | 后台/财务管理/提现记录/提现渠道列表-cold.bru |
| P0-069 | manual_review | finance | POST | {{admin_url}}/admin/finance/transaction/list?cash_type=2001&page=1&page_size=5 |  | 后台/财务管理/会员钱包账变/账变列表- wesley.bru |
| P0-070 | manual_review | finance | POST | {{admin_url}}/admin/finance/withdraw/agree |  | 后台/风控管理/存-提审核/提现同意-wesley.bru |
| P0-071 | manual_review | finance | POST | {{admin_url}}/admin/finance/withdraw/batch/agree |  | 后台/风控管理/存-提审核/批量提现同意-cold.bru |
| P0-072 | manual_review | finance | POST | {{admin_url}}/admin/finance/withdraw/batch/reject |  | 后台/风控管理/存-提审核/批量提现拒绝-cold.bru |
| P0-073 | manual_review | finance | POST | {{admin_url}}/admin/finance/withdraw/export |  | 后台/财务管理/提现记录/提现记录导出-wesley.bru |
| P0-074 | manual_review | finance | POST | {{admin_url}}/admin/finance/withdraw/fail |  | 后台/风控管理/存-提审核/出款失败-wesley.bru |
| P0-075 | manual_review | finance | POST | {{admin_url}}/admin/finance/withdraw/list |  | 后台/财务管理/提现记录/提现列表-wesley.bru |
| P0-076 | manual_review | finance | POST | {{admin_url}}/admin/finance/withdraw/reject?id=2 |  | 后台/风控管理/存-提审核/提现拒绝-wesley.bru |
| P0-077 | manual_review | finance | POST | {{admin_url}}/admin/finance/withdraw/risk/audit/export | hardcoded_env | 后台/风控管理/存-提审核/提现审核列表导出.bru |
| P0-078 | manual_review | finance | GET | {{admin_url}}/admin/finance/withdraw/risk/audit/list |  | 后台/风控管理/存-提审核/提现审核列表-wesley.bru |
| P0-079 | manual_review | finance | POST | {{admin_url}}/admin/finance/withdraw/success |  | 后台/风控管理/存-提审核/出款成功-wesley.bru |
| P0-080 | manual_review | finance | POST | {{admin_url}}/admin/finance/withdraw/sync?id=3 |  | 后台/财务管理/提现记录/提现同步状态-wesley.bru |
