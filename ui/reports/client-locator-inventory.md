# 客户端 UI 定位资产扫描

- 扫描时间：2026-08-26T07:32:19.471Z
- Base URL：https://client-fat.filbet2025.com
- 目标：按页面沉淀 Playwright 可用定位资产，优先用于后续数据驱动 UI 自动化和接口链路补全。

## 页面汇总

| 页面 | URL | 定位资产数 | 入口 |
|---|---|---:|---|
| 登录注册 | `https://client-fat.filbet2025.com/login` | 13 | path:/login |
| 首页 | `https://client-fat.filbet2025.com/` | 124 | path:/ |
| Game | `https://client-fat.filbet2025.com/slots` | 9 | path:/slots |
| Rewards | `https://client-fat.filbet2025.com/bonus` | 9 | path:/bonus |
| Filcoin | `https://client-fat.filbet2025.com/coin` | 9 | path:/coin |
| My | `https://client-fat.filbet2025.com/user` | 9 | path:/user |

## 页面定位资产

### 登录注册

| 类型 | 文案/占位 | role | selector hint | enabled |
|---|---|---|---|---:|
| button:button | Password |  | `button:has-text("Password")` | true |
| button:button | SMS OTP |  | `button:has-text("SMS\ OTP")` | true |
| input:tel | 900 000 0000 |  | `input[placeholder="\39 00\ 000\ 0000"]` | true |
| input:password | Enter Password |  | `input[name="password"]` | true |
| button | Login |  | `button:has-text("Login")` | false |
| button | Forgot Password |  | `button:has-text("Forgot\ Password")` | true |
| button:button | Continue with facebook |  | `button` | true |
| a | Terms of Use |  | `a:has-text("Terms\ of\ Use")` | true |
| a | Privacy Policy |  | `a:has-text("Privacy\ Policy")` | true |
| button:button | Register here. |  | `button:has-text("Register\ here\.")` | true |
| button:button | Online Support |  | `button:has-text("Online\ Support")` | true |
| button | Exit |  | `button:has-text("Exit")` | true |
| button | Proceed |  | `button:has-text("Proceed")` | false |

### 首页

| 类型 | 文案/占位 | role | selector hint | enabled |
|---|---|---|---|---:|
| button:button | Menu |  | `button` | true |
| button:button | Register / Login |  | `button:has-text("Register\ \/\ Login")` | true |
| button:button | Search |  | `button:has-text("Search")` | true |
| button:button | Popular |  | `button:has-text("Popular")` | true |
| button:button | Highest RTP |  | `button:has-text("Highest\ RTP")` | true |
| button:button | Top Multipliers |  | `button:has-text("Top\ Multipliers")` | true |
| button:button | 2 |  | `button:has-text("\32 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 2 |  | `button:has-text("\32 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | 1 |  | `button:has-text("\31 ")` | true |
| button:button | Refresh |  | `button` | true |
| button:button | More |  | `button:has-text("More")` | true |
| button:button | More |  | `button:has-text("More")` | true |
| button:button | More |  | `button:has-text("More")` | true |
| button:button | mi |  | `button` | true |
| button:button | jili |  | `button` | true |
| button:button | playstar |  | `button` | true |
| button:button | uu |  | `button` | true |
| button:button | netent |  | `button` | true |
| button:button | redtiger |  | `button` | true |
| button:button | btg |  | `button` | true |
| button:button | nlc |  | `button` | true |
| button:button | maxwin |  | `button` | true |
| button:button | yellowbat |  | `button` | true |
| button:button | pp |  | `button` | true |
| button:button | funky |  | `button` | true |
| button:button | galaxsys |  | `button` | true |
| button:button | fastspin |  | `button` | true |
| button:button | habanero |  | `button` | true |
| button:button | mi |  | `button` | true |
| button:button | jili |  | `button` | true |
| button:button | playstar |  | `button` | true |
| button:button | uu |  | `button` | true |
| button:button | netent |  | `button` | true |
| button:button | redtiger |  | `button` | true |
| button:button | btg |  | `button` | true |
| button:button | nlc |  | `button` | true |
| button:button | maxwin |  | `button` | true |
| button:button | yellowbat |  | `button` | true |
| button:button | pp |  | `button` | true |
| button:button | funky |  | `button` | true |
| button:button | galaxsys |  | `button` | true |
| button:button | fastspin |  | `button` | true |
| button:button | habanero |  | `button` | true |

### Game

| 类型 | 文案/占位 | role | selector hint | enabled |
|---|---|---|---|---:|
| button:button | Refresh |  | `button:has-text("Refresh")` | true |
| button:button | Back to Home |  | `button:has-text("Back\ to\ Home")` | true |
| a | Home |  | `a:has-text("Home")` | true |
| a | Game |  | `a:has-text("Game")` | true |
| a | Rewards |  | `a:has-text("Rewards")` | true |
| a | Filcoin |  | `a:has-text("Filcoin")` | true |
| a | My |  | `a:has-text("My")` | true |
| button | Exit |  | `button:has-text("Exit")` | true |
| button | Proceed |  | `button:has-text("Proceed")` | false |

### Rewards

| 类型 | 文案/占位 | role | selector hint | enabled |
|---|---|---|---|---:|
| button:button | Refresh |  | `button:has-text("Refresh")` | true |
| button:button | Back to Home |  | `button:has-text("Back\ to\ Home")` | true |
| a | Home |  | `a:has-text("Home")` | true |
| a | Game |  | `a:has-text("Game")` | true |
| a | Rewards |  | `a:has-text("Rewards")` | true |
| a | Filcoin |  | `a:has-text("Filcoin")` | true |
| a | My |  | `a:has-text("My")` | true |
| button | Exit |  | `button:has-text("Exit")` | true |
| button | Proceed |  | `button:has-text("Proceed")` | false |

### Filcoin

| 类型 | 文案/占位 | role | selector hint | enabled |
|---|---|---|---|---:|
| button:button | Refresh |  | `button:has-text("Refresh")` | true |
| button:button | Back to Home |  | `button:has-text("Back\ to\ Home")` | true |
| a | Home |  | `a:has-text("Home")` | true |
| a | Game |  | `a:has-text("Game")` | true |
| a | Rewards |  | `a:has-text("Rewards")` | true |
| a | Filcoin |  | `a:has-text("Filcoin")` | true |
| a | My |  | `a:has-text("My")` | true |
| button | Exit |  | `button:has-text("Exit")` | true |
| button | Proceed |  | `button:has-text("Proceed")` | false |

### My

| 类型 | 文案/占位 | role | selector hint | enabled |
|---|---|---|---|---:|
| button:button | Refresh |  | `button:has-text("Refresh")` | true |
| button:button | Back to Home |  | `button:has-text("Back\ to\ Home")` | true |
| a | Home |  | `a:has-text("Home")` | true |
| a | Game |  | `a:has-text("Game")` | true |
| a | Rewards |  | `a:has-text("Rewards")` | true |
| a | Filcoin |  | `a:has-text("Filcoin")` | true |
| a | My |  | `a:has-text("My")` | true |
| button | Exit |  | `button:has-text("Exit")` | true |
| button | Proceed |  | `button:has-text("Proceed")` | false |

## 捕获接口

| Method | HTTP | URL |
|---|---:|---|
| GET | 200 | `https://client-fat.filbet2025.com/member/fb/list` |
| GET | 200 | `https://client-fat.filbet2025.com/member/buriedPoint/detailV2?ad_id=` |
| POST | 200 | `https://client-fat.filbet2025.com/member/channel/trackclick` |
| POST | 200 | `https://client-fat.filbet2025.com/member/game/rank` |
| GET | 200 | `https://client-fat.filbet2025.com/member/materials/list?platform_code=filbet&material_type_code=homepagebanner` |
| GET | 200 | `https://client-fat.filbet2025.com/member/materials/list?platform_code=filbet&material_type_code=logo` |
| GET | 200 | `https://client-fat.filbet2025.com/member/materials/list?platform_code=filbet&material_type_code=socialmedia` |
| GET | 200 | `https://client-fat.filbet2025.com/member/index` |
| GET | 200 | `https://client-fat.filbet2025.com/member/v2/index` |
| GET | 200 | `https://client-fat.filbet2025.com/member/marquee/list?ty=0` |
| GET | 200 | `https://client-fat.filbet2025.com/member/bigprize/list` |
| GET | 200 | `https://client-fat.filbet2025.com/member/system` |
| GET | 200 | `https://client-fat.filbet2025.com/member/materials/list?platform_code=filbet&material_type_code=singup` |
| GET | 200 | `https://client-fat.filbet2025.com/filcoin/rewards` |

## 原始结果

- JSON：`ui/results/client-locator-inventory.json`
