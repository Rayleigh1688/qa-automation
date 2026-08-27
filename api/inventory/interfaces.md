# Bruno 接口资产扫描

扫描来源：`/Users/rayleigh/API/FB/filbet`

全量明细：`/Users/rayleigh/qa-automation/api/inventory/interfaces.csv`

## 总览

| 指标 | 数量 |
| --- | --- |
| Bruno 文件 | 1133 |
| HTTP 请求 | 908 |
| 可用 URL 请求 | 901 |
| 非请求或未解析请求 | 225 |
| URL 含 /v2 | 4 |
| 文件名/目录含 v2 但 URL 非 /v2 | 15 |
| todo 标记 | 83 |
| 弃用标记 | 2 |
| 老接口或 copy 标记 | 10 |
| 硬编码环境 URL | 264 |
| 可归一到 {{api_url}} | 175 |
| 可归一到 {{admin_url}} | 585 |
| 可归一到 {{agency_url}} | 55 |
| P0 候选请求 | 164 |

## 业务域分布

| 业务域 | 文件数 |
| --- | --- |
| 后台 | 523 |
| 前台 | 185 |
| 活动 | 156 |
| 合规 | 95 |
| 代理管理后台 | 88 |
| 游戏集成平台 | 43 |
| 代理后台 | 27 |
| environments | 7 |
| mx | 4 |
| 免费旋转 | 3 |
| (root) | 2 |

## 方法分布

| 方法 | 数量 |
| --- | --- |
| GET | 524 |
| POST | 382 |
| NO_METHOD | 225 |
| PUT | 2 |

## Host 与环境变量分布

| Host/变量 | 请求数 |
| --- | --- |
| {{admin_url}} | 287 |
| (relative_abs) | 128 |
| admin-fat.filbet2025.com | 96 |
| client-fat.filbet2025.com | 70 |
| {{api_url}} | 55 |
| {{test_url}} | 47 |
| admin-antd.filbet2025.com | 31 |
| {{cbor_request_proxy}} | 27 |
| 127.0.0.1:7095 | 26 |
| {{angency}} | 24 |
| {{admin_url_new}} | 23 |
| {{admin_domain}} | 13 |

## 建议 URL 变量分布

| 建议变量 | 请求数 |
| --- | --- |
| {{admin_url}} | 585 |
| {{api_url}} | 175 |
| (empty) | 93 |
| {{agency_url}} | 55 |

## 初步判断

- 该集合同时包含前台、后台、活动、合规、代理后台、游戏集成平台等多个业务域。
- `/v2` 不能只按 URL 判断；有些新版模块体现在文件名或目录，例如 `Vipv2`。
- `todo`、`弃用`、`老页面`、`旧`、`copy`、硬编码环境 URL 都需要在正式自动化前单独复核。
- `client-fat.filbet2025.com`、`client-beta.filbet2025.com` 等客户端硬编码地址建议归一为 `{{api_url}}`。
- `admin-fat.filbet2025.com`、`admin-antd.filbet2025.com` 等后台硬编码地址建议归一为 `{{admin_url}}`。
- P0 候选应先从前台登录注册、财务、游戏、KYC、会员信息，以及后台风控和财务审核相关接口中筛选。

## P0 候选接口

以下是按规则初筛的前 80 条 P0 候选，仍需人工确认是否仍在线上使用、是否有副作用、是否适合自动化。

| 业务域 | 方法 | Path | 建议变量 | 标记 | 文件 |
| --- | --- | --- | --- | --- | --- |
| finance | POST | /admin/finance/adjust/list | {{admin_url}} |  | 代理管理后台/财务管理/财务报表/系统调整.bru |
| finance | POST | /agency/finance/transaction/list | {{agency_url}} | hardcoded_env | 代理管理后台/财务管理/财务报表/账变列表- wesley.bru |
| finance | GET | /agency/finance/transaction/types | {{admin_url}} |  | 代理管理后台/财务管理/财务报表/账变类型- wesley.bru |
| member | GET | /member/vip/rule | {{api_url}} | todo | 前台/VIP/VIP配置规则-todo.bru |
| member | GET | /member/vip/level/detail | {{api_url}} | hardcoded_env | 前台/VIP/会员vip等级详情.bru |
| kyc | GET | /member/kyc/ekyc/info | {{api_url}} | hardcoded_env | 前台/kyc/ekyc 配置.bru |
| kyc | POST | /member/kyc/ekyc/callback | {{api_url}} | hardcoded_env | 前台/kyc/ekyc回调.bru |
| kyc | POST | /member/kyc/v2/insert | {{api_url}} | url_v2,hardcoded_env | 前台/kyc/v2/insert.bru |
| kyc | POST | /member/kyc/insert | {{api_url}} |  | 前台/kyc/提交 kyc -- double-cold-owen.bru |
| kyc | POST | /member/kyc/base | {{api_url}} |  | 前台/kyc/提交 kyc 基础信息 -- double-cold.bru |
| kyc | GET | /member/kyc/detail | {{api_url}} |  | 前台/kyc/获取 kyc 详情 -- double-cold.bru |
| kyc | GET | /member/kyc/ekyc/url | {{api_url}} | hardcoded_env | 前台/kyc/获取ekyc的url.bru |
| kyc | GET | /member/kyc/ekyc/get_results | {{api_url}} | hardcoded_env | 前台/kyc/获取ekyc结果.bru |
| kyc | POST | /member/kyc/shops | {{api_url}} |  | 前台/kyc/获取门店列表 -- owen.bru |
| auth,finance | POST | /finance/lazadaminiapp/login | {{api_url}} |  | 前台/lazada mini/登陆-owen.bru |
| finance | POST | /cmpl/wallet/information | {{api_url}} | hardcoded_env | 前台/mx/information.bru |
| finance | POST | /cmpl/wallet/playerid | {{api_url}} | hardcoded_env | 前台/mx/playerid.bru |
| kyc | POST | /member/ocr/setup | {{api_url}} |  | 前台/ocr/初始化ZOLOZ中的身份验证进程.bru |
| kyc | POST | /member/ocr/checkresult | {{api_url}} |  | 前台/ocr/获取身份验证进程的运行状态和相关的验证结果-double-owen.bru |
| kyc | POST | /member/flutter/ocr/setup | {{api_url}} |  | 前台/ocr-flutter/初始化ZOLOZ中的身份验证进程.bru |
| kyc | POST | /member/flutter/ocr/checkresult | {{api_url}} |  | 前台/ocr-flutter/获取身份验证进程的运行状态和相关的验证结果.bru |
| kyc | POST | /member/oss/upload | {{admin_url}} |  | 前台/oss/上传 kyc 相关图片 - double.bru |
| auth | POST | /member/fb/login | {{api_url}} | hardcoded_env | 前台/三方登录/注册接口.bru |
| member | GET | /member/agency/audit/results | {{api_url}} | hardcoded_env | 前台/代理/代理审核结果.bru |
| member | GET | /member/agency/problem/list | {{api_url}} | hardcoded_env | 前台/代理/代理申请问题列表.bru |
| member | POST | /member/agency/apply/material | {{api_url}} | hardcoded_env | 前台/代理/申请资料提交.bru |
| finance | GET | /promo/task/transaction | {{api_url}} |  | 前台/任务中心/代币明细-seven.bru |
| auth | POST | /member/bind/facebook | {{api_url}} |  | 前台/会员信息/facebook oauth绑定-ducky.bru |
| auth | GET | /member/facebook_link | {{api_url}} |  | 前台/会员信息/facebook oauth链接-ducky.bru |
| auth | POST | /member/bind/google | {{api_url}} |  | 前台/会员信息/google oauth绑定-ducky.bru |
| auth | GET | /member/google_link | {{api_url}} |  | 前台/会员信息/google oauth链接-ducky.bru |
| member | POST | /member/agency/apply | {{api_url}} |  | 前台/会员信息/代理申请.bru |
| member | GET | /member/vip | {{api_url}} |  | 前台/会员信息/会员vip信息-seven.bru |
| member | POST | /member/detail/update | {{api_url}} |  | 前台/会员信息/会员信息修改-seven.bru |
| member | POST | /member/card/update | {{api_url}} |  | 前台/会员信息/会员卡片列表更新-owen.bru |
| member | POST | /member/card/list | {{api_url}} |  | 前台/会员信息/会员卡片列表查询-owen.bru |
| auth | POST | /member/password/update | {{api_url}} |  | 前台/会员信息/密码修改-seven.bru |
| auth,finance | POST | /member/wallet/checkpassword | {{api_url}} |  | 前台/会员信息/校验钱包密码-ducky.bru |
| member | GET | /member/detail | {{api_url}} | hardcoded_env | 前台/会员信息/获取会员信息-seven-aliang(20260424).bru |
| auth,finance | POST | /member/wallet/password/update | {{api_url}} |  | 前台/会员信息/设置新钱包密码-ducky.bru |
| auth | POST | /member/retrieve/passwordbyemail | {{api_url}} |  | 前台/会员信息/通过邮箱修改密码-ducky.bru |
| auth | POST | /member/auth/mail | {{api_url}} |  | 前台/会员信息/邮箱验证码验证-ducky.bru |
| auth,finance | POST | /member/wallet/password | {{api_url}} |  | 前台/会员信息/钱包密码设置-ducky.bru |
| auth | POST | /member/facebook/login | {{api_url}} |  | 前台/会员登陆注册验证/facebook oauth登录-ducky.bru |
| auth | POST | /member/google/login | {{api_url}} |  | 前台/会员登陆注册验证/google oauth登录-ducky.bru |
| auth | POST | /member/otp/login | {{api_url}} |  | 前台/会员登陆注册验证/otp登陆-seven.bru |
| auth | POST | /member/otp/login/v2 | {{api_url}} | url_v2 | 前台/会员登陆注册验证/otp登陆V2-seven.bru |
| auth | GET | /member/refresh/token | {{api_url}} |  | 前台/会员登陆注册验证/刷新token-seven.bru |
| auth | POST | /member/login | {{api_url}} |  | 前台/会员登陆注册验证/密码登陆-seven.bru |
| auth | POST | /member/v2/login | {{api_url}} | url_v2 | 前台/会员登陆注册验证/密码登陆v2-ducky.bru |
| auth | POST | /member/auth/password | {{api_url}} | old_or_copy | 前台/会员登陆注册验证/旧密码前置验证-seven.bru |
| auth | POST | /member/register | {{api_url}} | hardcoded_env | 前台/会员登陆注册验证/注册.bru |
| auth | POST | /member/sms | {{api_url}} |  | 前台/会员登陆注册验证/短信发送-seven.bru |
| auth | POST | /member/auth/sms | {{api_url}} |  | 前台/会员登陆注册验证/短信验证码前置检查-seven.bru |
| auth | GET | /member/logout | {{api_url}} |  | 前台/会员登陆注册验证/退出登陆-seven.bru |
| auth | POST | /member/retrieve/password | {{api_url}} |  | 前台/会员登陆注册验证/重置密码-seven.bru |
| finance | POST | /finance/payment/callback/deposit/pisopay | {{api_url}} | hardcoded_env | 前台/支付/pisopay回调.bru |
| game | GET | /member/fav/delete | {{api_url}} |  | 前台/游戏/删除游戏收藏-light.bru |
| game | GET | /member/game/list/history | {{api_url}} |  | 前台/游戏/历史游戏列表-light.bru |
| game | GET | /member/game/list/recommend | {{api_url}} | hardcoded_env | 前台/游戏/推荐列表-benjie.bru |
| game | GET | /member/game/list/recent | {{api_url}} |  | 前台/游戏/最近游戏-benjie.bru |
| game | GET | /member/fav/insert | {{api_url}} |  | 前台/游戏/添加游戏收藏-light.bru |
| game | GET | /member/game/list | {{api_url}} |  | 前台/游戏/游戏列表-light.bru |
| game | GET | /member/fav/list | {{api_url}} |  | 前台/游戏/游戏收藏列表-light.bru |
| game | GET | /member/game/listRw | {{api_url}} | hardcoded_env | 前台/游戏/游戏查询语句组合-benjie.bru |
| game | GET | /member/game/bet/list | {{api_url}} |  | 前台/游戏/游戏记录-wesley.bru |
| game | GET | /member/v2/index | {{api_url}} | url_v2,hardcoded_env | 前台/游戏/首页缓存v2-owen.bru |
| finance | POST | /finance/lazada/exchange | {{api_url}} |  | 前台/财务/lazada兑换-owen.bru |
| finance | POST | /finance/lazada/product/list | {{api_url}} |  | 前台/财务/lazada商品列表-owen.bru |
| finance | GET | /finance/wallet | {{api_url}} |  | 前台/财务/会员钱包-wesley.bru |
| finance | GET | /finance/payment/deposit | {{api_url}} |  | 前台/财务/充值-wesley-cold.bru |
| finance | GET | /finance/deposit/list | {{api_url}} |  | 前台/财务/充值记录-wesley.bru |
| finance | GET | /finance/deposit/detail | {{api_url}} |  | 前台/财务/充值详情.bru |
| finance | POST | /finance/account/insert | {{api_url}} | hardcoded_env | 前台/财务/创建提现账户-wesley.bru |
| finance | POST | /finance/account/bank/delete | {{api_url}} | hardcoded_env | 前台/财务/删除银行卡.bru |
| finance | GET | /finance/account/delete | {{api_url}} |  | 前台/财务/提款账号删除-wesley.bru |
| finance | GET | /finance/account/list | {{api_url}} | hardcoded_env | 前台/财务/提款账户列表-wesley.bru |
| finance | GET | /finance/payment/withdraw | {{api_url}} | hardcoded_env | 前台/财务/提现-wesley-cold.bru |
| finance | GET | /finance/payment/tab/list | {{api_url}} | hardcoded_env | 前台/财务/提现tab.bru |
| finance | GET | /finance/withdraw/list | {{api_url}} |  | 前台/财务/提现记录-wesley.bru |

## 需复核接口样本

以下是带 `todo`、弃用、老接口、异常相对路径等标记的样本。全量请查看 CSV。

| 标记 | 方法 | Path | 文件 |
| --- | --- | --- | --- |
| old_or_copy,hardcoded_env | GET | /agency/member/list | 代理后台/会员列表/会员列表 copy.bru |
| hardcoded_env,odd_relative_url | POST | /agency/pwd/login | 代理后台/登陆/密码登陆-wesley.bru |
| odd_relative_url | GET | /agency/priv/list | 代理管理后台/系统/角色配置/权限列表.bru |
| todo | GET | /member/vip/rule | 前台/VIP/VIP配置规则-todo.bru |
| deprecated | POST | /member/kyc/update | 前台/kyc/更新 kyc -- double-cold（已经弃用，请调用 -kyc-insert）.bru |
| old_or_copy | POST | /member/auth/password | 前台/会员登陆注册验证/旧密码前置验证-seven.bru |
| todo | GET | /member/buriedPoint/detail | 前台/埋点/埋点详情-todo.bru |
| todo,name_v2 | GET | /member/buriedPoint/detailV2 | 前台/埋点/埋点详情V2-todo.bru |
| todo | GET | /member/channel/detail | 前台/渠道/渠道详情-todo.bru |
| todo | POST | /member/channel/trackclick | 前台/渠道/渠道跟踪点击-todo.bru |
| todo,hardcoded_env | GET | /member/message/has_unread | 前台/站内信/是否有未读信息-todo.bru |
| todo,hardcoded_env | GET | /member/message/list | 前台/站内信/站内信列表-todo.bru |
| todo,hardcoded_env | POST | /member/message/reads | 前台/站内信/站内信已读-todo.bru |
| todo,hardcoded_env | GET | /member/message/popup_list | 前台/站内信/获取弹窗站内信列表-todo.bru |
| todo | GET | /member/popup/list | 前台/配置/首页弹窗/获取首页弹窗列表-todo.bru |
| todo,hardcoded_env | GET | /admin/vip/level/range/detail | 后台/VIP/VIP等级区间详情-todo.bru |
| todo,hardcoded_env | GET | /admin/vip/level/list | 后台/VIP/VIP配置列表-todo.bru |
| todo,hardcoded_env | POST | /admin/vip/level/update | 后台/VIP/VIP配置编辑-todo.bru |
| todo,hardcoded_env | GET | /admin/vip/level/detail | 后台/VIP/VIP配置详情-todo.bru |
| todo,hardcoded_env | GET | /admin/todo/reminder | 后台/其它/待办事项提示器-todo.bru |
| todo,hardcoded_env | GET | /admin/rechargeCard/listForSelect | 后台/其它/获取充值卡下拉列表-todo.bru |
| todo,hardcoded_env | GET | /admin/mall/goods/import | 后台/商城管理/产品导入-todo.bru |
| todo,hardcoded_env | GET | /admin/mall/goods/export | 后台/商城管理/产品导出-todo.bru |
| todo,hardcoded_env | GET | /admin/mall/goods/detail | 后台/商城管理/产品详情-todo.bru |
| todo,hardcoded_env | POST | /admin/mall/goods/insert | 后台/商城管理/新增商城商品-todo.bru |
| todo,hardcoded_env | POST | /admin/mall/goods/update | 后台/商城管理/更新商城商品-todo.bru |
| todo,hardcoded_env | GET | /admin/mall/goods/list | 后台/商城管理/获取产品列表-todo.bru |
| todo,hardcoded_env | GET | /admin/mall/order/list | 后台/商城订单记录/商城订单列表-todo.bru |
| todo,hardcoded_env | GET | /admin/mall/order/export | 后台/商城订单记录/商城订单导出-todo.bru |
| todo,hardcoded_env | GET | /admin/mall/order/detail | 后台/商城订单记录/商城订单详情-todo.bru |
| todo,hardcoded_env | POST | /admin/mall/order/delivery | 后台/商城订单记录/手动发货-todo.bru |
| todo,hardcoded_env | POST | /admin/buriedPoint/update | 后台/埋点/修改埋点-todo.bru |
| todo,hardcoded_env | POST | /admin/buriedPoint/delete | 后台/埋点/删除埋点-todo.bru |
| todo,hardcoded_env | GET | /admin/buriedPoint/list | 后台/埋点/埋点列表-todo.bru |
| todo,hardcoded_env | POST | /admin/buriedPoint/insert | 后台/埋点/新增埋点-todo.bru |
| todo,hardcoded_env | GET | /admin/domain/listForSelect | 后台/域名/域名选项列表-todo.bru |
| todo,hardcoded_env | GET | /admin/domain/listForSelect | 后台/域名/获取域名下拉列表-todo.bru |
| todo,hardcoded_env | GET | /admin/filcoin/order/list | 后台/财务管理/代币商城订单/代币商城订单列表-todo.bru |
| todo,hardcoded_env | GET | /admin/filcoin/order/export | 后台/财务管理/代币商城订单/代币商城订单导出-todo.bru |
| todo,hardcoded_env | GET | /admin/banner/user/count | 后台/轮播图-首页弹窗/名单数量-todo.bru |
| todo,hardcoded_env | GET | /admin/banner/user/list | 后台/轮播图-首页弹窗/查看名单-todo.bru |
| todo | GET | /admin/channel/promoData/list | 后台/运营管理/推广管理/推广数据/推广数据列表-todo.bru |
| todo | GET | /admin/channel/promoData/logs | 后台/运营管理/推广管理/推广数据/推广数据日志-todo.bru |
| todo | GET | /admin/channel/promoData/detail | 后台/运营管理/推广管理/推广数据/推广数据详细-todo.bru |
| todo | GET | /admin/channel/promoData/consumption | 后台/运营管理/推广管理/推广数据/推广数据面板消耗详情-todo.bru |
| todo | POST | /admin/channel/promoData/update | 后台/运营管理/推广管理/推广数据/更新推广数据-todo.bru |
| todo | POST | /admin/channel/promoData/update/consumption | 后台/运营管理/推广管理/推广数据/更新推广数据面板消耗-todo.bru |
| todo | POST | /admin/channel/manage/delete | 后台/运营管理/推广管理/渠道管理/删除渠道管理-todo.bru |
| todo | POST | /admin/channel/manage/insert | 后台/运营管理/推广管理/渠道管理/新增渠道管理-todo.bru |
| todo | POST | /admin/channel/manage/update | 后台/运营管理/推广管理/渠道管理/更新渠道管理-todo.bru |
| todo | POST | /admin/channel/manage/update/group | 后台/运营管理/推广管理/渠道管理/更新渠道管理分组-todo.bru |
| todo | POST | /admin/channel/manage/update/state | 后台/运营管理/推广管理/渠道管理/更新渠道管理状态-todo.bru |
| todo | POST | /admin/channel/group/delete | 后台/运营管理/推广管理/渠道管理/渠道分组/删除渠道分组-todo.bru |
| todo | POST | /admin/channel/group/insert | 后台/运营管理/推广管理/渠道管理/渠道分组/新增渠道分组-todo.bru |
| todo | POST | /admin/channel/group/update | 后台/运营管理/推广管理/渠道管理/渠道分组/更新渠道分组-todo.bru |
| todo | GET | /admin/channel/group/list | 后台/运营管理/推广管理/渠道管理/渠道分组/渠道分组列表-todo.bru |
| todo | GET | /admin/channel/group/dict | 后台/运营管理/推广管理/渠道管理/渠道分组/渠道分组字黄-todo.bru |
| todo | POST | /admin/channel/exchangeRate/update | 后台/运营管理/推广管理/渠道管理/渠道汇率/更新渠道汇率-todo.bru |
| todo | GET | /admin/channel/exchangeRate/list | 后台/运营管理/推广管理/渠道管理/渠道汇率/渠道汇率列表-todo.bru |
| todo | GET | /admin/channel/manage/list | 后台/运营管理/推广管理/渠道管理/渠道管理列表-todo.bru |
| todo | GET | /admin/channel/manage/dict | 后台/运营管理/推广管理/渠道管理/渠道管理字典-todo.bru |
| todo | GET | /admin/channel/manage/export | 后台/运营管理/推广管理/渠道管理/渠道管理导出-todo.bru |
| todo | GET | /admin/channel/manage/detail | 后台/运营管理/推广管理/渠道管理/渠道管理详情-todo.bru |
| todo | GET | /admin/reports/channel | 后台/运营管理/日常报表/渠道业绩/渠道报表-todo.bru |
| todo | GET | /admin/reports/channel | 后台/运营管理/日常报表/渠道业绩/渠道报表导出-todo.bru |
| todo | GET | /admin/reports/channel/detail | 后台/运营管理/日常报表/渠道业绩/渠道报表明细-todo.bru |
| todo | GET | /admin/reports/channel/detail/export | 后台/运营管理/日常报表/渠道业绩/渠道报表明细导出-todo.bru |
| todo | POST | /admin/message/templates/update | 后台/运营管理/消息模板/更新消息模板-todo.bru |
| todo | GET | /admin/message/templates/export | 后台/运营管理/消息模板/消息模板导出-todo.bru |
| todo | GET | /admin/message/templates/list | 后台/运营管理/消息模板/获取消息模板列表-todo.bru |
| todo | GET | /admin/domain/delete | 后台/运营管理/渠道管理/域名库管理/删除域名-todo.bru |
| todo | POST | /admin/domain/list | 后台/运营管理/渠道管理/域名库管理/域名列表-todo.bru |
| todo | POST | /admin/domain/export | 后台/运营管理/渠道管理/域名库管理/域名列表导出-todo.bru |
| todo | GET | /admin/domain/menus | 后台/运营管理/渠道管理/域名库管理/域名菜单-todo.bru |
| todo | POST | /admin/domain/insert | 后台/运营管理/渠道管理/域名库管理/新增域名-todo.bru |
| todo | POST | /admin/domain/update | 后台/运营管理/渠道管理/域名库管理/编辑域名-todo.bru |
| todo | GET | /admin/channel/delete | 后台/运营管理/渠道管理/引流渠道管理/删除渠道-todo.bru |
| todo | POST | /admin/channel/insert | 后台/运营管理/渠道管理/引流渠道管理/新增渠道-todo.bru |
| todo | POST | /admin/channel/list | 后台/运营管理/渠道管理/引流渠道管理/渠道列表-todo.bru |
