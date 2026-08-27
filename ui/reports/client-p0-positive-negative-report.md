# 客户端 P0 UI 正反例执行报告

- 执行时间: 2026-08-26T09:47:42.431Z
- 用例数: 5

| 用例 | 结果 | URL | 关键说明 |
|---|---|---|---|
| negative_missing_otp | passed | `/?action=login&payload=<redacted>` | 手机号已填写但 OTP 为空，应保持未登录态 |
| negative_unchecked_terms | passed | `/?action=login&payload=<redacted>` | 未勾选登录条款时不能进入会员态 |
| negative_guest_my | passed | `/` | 未登录访问 My 不应暴露会员账号、KYC、钱包等敏感信息 |
| positive_logged_in_my_exposes_wallet_and_member_checkpoints | blocked | `/?action=login&payload=<redacted>` | 测试账号当前无法登录，无法继续验证登录后页面 |
| negative_invalid_game_page_does_not_launch_third_party_game | blocked | `/?action=login&payload=<redacted>` | 测试账号当前无法登录，无法继续验证登录后页面 |
