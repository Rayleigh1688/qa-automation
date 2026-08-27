# 客户端 P0 主流程 UI 扫描报告

- 扫描时间: 2026-08-26T09:16:21.858Z
- Base URL: https://client-fat.filbet2025.com
- 页面数: 5
- Network 响应数: 82

## 页面扫描

| 模块 | 最终 URL | 定位资产数 | 入口方式 | 备注 |
|---|---|---:|---|---|
| 首页 | `/` | 20 | current:https://client-fat.filbet2025.com/?action=login&payload=omRzdGVwbmxvZ2luLXBhc3N3b3JkZGRhdGH3 |  |
| Game | `/s-game-category-v2/gameType/3` | 20 | text:Game |  |
| Rewards | `/welfare` | 20 | text:Rewards |  |
| Filcoin | `/s-points-v2` | 20 | text:Filcoin |  |
| My | `/my` | 20 | text:My |  |

## 关键接口响应

| Status | URL |
|---:|---|
| 200 | `/member/fb/list` |
| 200 | `/member/materials/list?platform_code=filbet&material_type_code=homepagebanner` |
| 200 | `/member/index` |
| 200 | `/member/v2/index` |
| 200 | `/member/materials/list?platform_code=filbet&material_type_code=logo` |
| 200 | `/member/materials/list?platform_code=filbet&material_type_code=socialmedia` |
| 200 | `/member/game/rank` |
| 200 | `/member/v2/index` |
| 200 | `/member/marquee/list?ty=0` |
| 200 | `/member/game/rank` |
| 200 | `/member/bigprize/list` |
| 200 | `/member/channel/trackclick` |
| 200 | `/member/buriedPoint/detailV2?ad_id=` |
| 200 | `/member/materials/list?platform_code=filbet&material_type_code=singup` |
| 200 | `/member/system` |
| 200 | `/member/sms` |
| 200 | `/member/otp/login/v2` |
| 200 | `/member/detail` |
| 200 | `/member/fav/list?page=1&page_size=1000` |
| 200 | `/member/v2/index` |
| 200 | `/finance/wallet` |
| 200 | `/member/message/popup_list` |
| 200 | `/member/kyc/detail` |
| 200 | `/member/detail` |
| 200 | `/member/message/has_unread` |
| 200 | `/member/message/popup_list` |
| 200 | `/member/materials/list?platform_code=filbet&material_type_code=popup` |
| 200 | `/member/game/listRw?sort=&venues=&game_types=3&query=&is_new=0&is_hot=0&page=1&page_size=15` |
| 200 | `/member/introduce/complex?brand=h5&ty=welfare` |
| 200 | `/promo/bonus/total` |
| 200 | `/promo/deposit/ladder/detail?pid=20` |
| 200 | `/member/filcoin/balance` |
| 200 | `/member/filcoin/balance` |
| 200 | `/member/message/has_unread` |
| 200 | `/member/materials/list?platform_code=filbet&material_type_code=socialmedia` |
| 200 | `/member/system` |
| 200 | `/promo/deposit/ladder/deposit/conf` |
| 200 | `/member/detail` |
| 200 | `/finance/wallet` |
| 200 | `/member/vip/level/detail` |
| 200 | `/member/message/has_unread` |
| 200 | `/member/detail` |
| 200 | `/member/vip/rule` |

## 下一步判断

- 登录后的首页、钱包、My 页可作为接口自动化的前置状态来源。
- 充值、提现、投注需要在页面扫描基础上继续补入口点击和 Network 捕获，避免只按接口文档猜参数。
- 活动、运营位只保留扫描资产，不纳入稳定 P0 断言。