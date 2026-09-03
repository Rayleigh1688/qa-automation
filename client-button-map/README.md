# 客户端页面与控件清单

## 用途

本目录按截图整理客户端当前可见页面、功能区域和可交互控件，主要用于：

- 指导后续 Playwright 按页面有序探索，避免漏点输入框、页签、按钮和列表项；
- 将页面初始化和用户操作与真实 Network 请求关联；
- 识别仅展示数据、点击后跳转、改变筛选条件或产生业务副作用的不同控件；
- 为后续接口分级和全量接口测试提供 UI 调用端证据。

本文件不是 P0 用例清单，也不直接记录接口是否通过。接口方法、路径、参数、状态和证据应保存在独立的接口映射资产中。

## 记录规则

1. 页面以各标题下标注的 PNG 截图为依据，红框按从左到右、从上到下记录。
2. 红框是功能范围提示；红框内部每个可点击控件仍需分别扫描。
3. 页面初始化后自动展示的数据区域也要记录，因为它们可能触发独立接口。
4. 同一控件在登录前后、不同页签或不同状态下可能调用不同接口，应分别验证。
5. 点击后进入的新页面，如果本目录没有对应截图，先记为“待补页面”，不假定其内部控件。
6. 活动 Banner、商品和游戏等动态内容以控件类型为准，不把某期名称或某个会员数据写成固定规则。
7. 不在本目录保存密码、OTP、Token、Cookie、手机号或未脱敏会员信息。

控件类型统一使用：`[展示]`、`[输入]`、`[按钮]`、`[页签]`、`[筛选]`、`[列表]`、`[卡片]`、`[跳转]`、`[状态]`。

## 页面清单

### 首页

截图：[`home.png`](home.png)

登录要求：基础浏览无需登录；收藏、启动游戏及会员相关入口的登录要求需要实际验证。

1. `[按钮]` 侧边栏菜单。
2. `[跳转]` Register / Login。
3. `[卡片]` 首页活动 Banner；点击后可能进入活动详情或游戏。
4. `[展示]` Daily Rewards：展示存款、投注进度及 Free Credit、Free Spin 奖励档位，不是普通“每日任务”。
5. `[列表]` New Games。
6. `[按钮]` New Games 刷新。
7. `[列表]` Hot Games。
8. `[列表]` Slot 等游戏分类区域。
9. `[卡片]` 游戏卡片；需要验证点击启动和登录拦截。
10. `[按钮]` 游戏收藏 / 取消收藏。
11. `[跳转]` 底部导航：Home、Game、Rewards、Filcoin、My。

### 侧边栏

截图：[`sidebar.png`](sidebar.png)

登录要求：打开侧边栏无需登录；各入口的游客行为分别验证。

1. `[跳转]` Login / Register。
2. `[跳转]` 游戏类型：Slots、Casino、Table、Bingo、Fishing、Arcade。
3. `[跳转]` Live RTP / 游戏排行榜。
4. `[跳转]` VIP Club。
5. `[跳转]` Live Support / 在线客服。
6. `[按钮]` Skins / 换肤。
7. `[跳转]` APP Download。

### 登录页

截图：[`login.png`](login.png)

登录要求：无需登录。

1. `[跳转]` 顶部活动或注册 Banner。
2. `[页签]` Password。
3. `[页签]` SMS OTP。
4. `[输入]` Phone Number。
5. `[输入]` Password；仅密码登录模式出现。
6. `[输入]` OTP；仅 SMS OTP 模式出现。
7. `[按钮]` Get Code；仅 SMS OTP 模式出现。
8. `[按钮]` Login。
9. `[跳转]` Forgot Password。
10. `[按钮]` Meta 登录。
11. `[按钮]` 用户协议勾选框。
12. `[跳转]` Terms of Use。
13. `[跳转]` Privacy Policy。
14. `[跳转]` Register here。
15. `[跳转]` Online Support。

### 注册页

截图：[`register.png`](register.png)

登录要求：无需登录。

1. `[跳转]` 顶部活动或登录 Banner。
2. `[输入]` Phone Number。
3. `[输入]` 验证码。
4. `[按钮]` Get Code。
5. `[输入]` Set password（页面标记为 optional）。
6. `[按钮]` 密码显示 / 隐藏。
7. `[输入]` Confirm password（页面标记为 optional）。
8. `[输入]` Referral / 邀请码（页面标记为 optional）。
9. `[按钮]` Register。
10. `[按钮]` Meta 注册 / 登录。
11. `[按钮]` 用户协议勾选框。
12. `[跳转]` Terms of Use。
13. `[跳转]` Privacy Policy。
14. `[跳转]` Log in。
15. `[跳转]` Online Support。

### 个人中心页（My）

截图：[`my-profile.png`](my-profile.png)

登录要求：需要登录。

1. `[按钮]` 换肤。
2. `[跳转]` 站内信 / 通知；包含未读状态。
3. `[跳转]` 在线客服。
4. `[展示]` 头像、昵称和会员 ID。
5. `[按钮]` 复制会员 ID。
6. `[跳转]` 个人资料详情。
7. `[展示]` 当前 VIP 等级和升级进度。
8. `[跳转]` VIP Center。
9. `[状态]` KYC Verification 状态。
10. `[跳转]` Verify Now / KYC 验证。
11. `[展示]` Total Balance。
12. `[按钮]` 刷新余额。
13. `[跳转]` Withdraw。
14. `[跳转]` Deposit。
15. `[跳转]` Transaction / 交易及账变记录。
16. `[跳转]` Bet History / 投注记录。
17. `[跳转]` Bonus / 彩金记录。
18. `[跳转]` Account / 提现账户。
19. `[卡片]` Apply To Become An Affiliate / 代理申请入口。

代理申请入口当前仍出现在 FAT 截图中。业务是否只取消“好友邀请”而保留“代理申请”，需要进一步确认；确认前不能直接标记为已下线。

### 活动主页（Rewards）

截图：[`rewards.png`](rewards.png)

登录要求：需要登录。

1. `[跳转]` 彩金领取记录。
2. `[展示]` My Filcoin 余额。
3. `[跳转]` My Filcoin。
4. `[展示]` My Free Spin 数量。
5. `[跳转]` My Free Spin。
6. `[按钮]` Lucky 7 说明。
7. `[跳转]` Daily Check-in Rewards。
8. `[展示]` 签到周期、日期和奖励状态。
9. `[按钮]` Check In；已签到状态应显示为不可重复执行。
10. `[页签]` All。
11. `[页签]` Newcomer。
12. `[页签]` Daily。
13. `[列表]` 活动 Banner / 活动卡片。
14. `[跳转]` 活动详情。

### 免费旋转页（My Free Spins）

截图：[`free-spins.png`](free-spins.png)

登录要求：需要登录。

1. `[展示]` Available for Use / 可用免费旋转次数。
2. `[展示]` Total Winnings / 免费旋转累计赢取金额。
3. `[状态]` 有效期或倒计时。
4. `[页签]` Available。
5. `[页签]` In Use。
6. `[页签]` Ended。
7. `[卡片]` 免费旋转活动或游戏卡片。
8. `[展示]` 单次投注额及 Spins 数量。
9. `[按钮]` Start Game。

### 商城任务主页（Earn Filcoins）

截图：[`earn-filcoins.png`](earn-filcoins.png)

登录要求：需要登录。

1. `[页签]` Earn Filcoins。
2. `[页签]` Filcoins Mall。
3. `[跳转]` 在线客服。
4. `[跳转]` FAQ。
5. `[展示]` My Filcoins 余额。
6. `[跳转]` Filcoins 明细或余额页。
7. `[展示]` 今日完成任务可获得的积分汇总。
8. `[列表]` Daily Tasks。
9. `[展示]` 单项任务进度、奖励和阶梯档位。
10. `[按钮]` 每项任务的 Go；应分别验证目标页面和请求。

产品展示名称暂统一写作 `Filcoins`；接口字段若使用 `coin` 或 `coins`，在接口映射中保留真实字段名。

### 商城主页（Filcoins Mall）

截图：[`filcoins-mall.png`](filcoins-mall.png)

登录要求：需要登录。

1. `[页签]` Earn Filcoins。
2. `[页签]` Filcoins Mall。
3. `[跳转]` 在线客服。
4. `[跳转]` FAQ。
5. `[展示]` My Filcoins 余额。
6. `[跳转]` Filcoins 明细或余额页。
7. `[筛选]` Popular 等商品排序。
8. `[筛选]` All Filcoins 等积分范围。
9. `[列表]` 商品列表。
10. `[卡片]` 商品图片、名称、库存和兑换价格。
11. `[跳转]` 商品详情。
12. `[按钮]` 兑换操作；当前截图未展示，进入商品详情后补充。

### 游戏主页（Game）

截图：[`games.png`](games.png)

登录要求：列表浏览可能无需登录；收藏和启动游戏需要实际验证登录拦截。

1. `[页签]` 游戏类型：Slot、Live、Table、Arcade、Lottery 等。
2. `[按钮]` 搜索。
3. `[筛选]` Sort by。
4. `[筛选]` Providers。
5. `[列表]` 当前筛选结果中的游戏。
6. `[卡片]` 游戏卡片；点击启动游戏。
7. `[按钮]` 收藏 / 取消收藏。
8. `[状态]` 下拉加载、翻页或无更多数据状态。

### 游戏厂商筛选弹窗（Game Providers）

截图：[`game-provider-filter.png`](game-provider-filter.png)

登录要求：与游戏主页一致。

1. `[按钮]` 关闭弹窗。
2. `[筛选]` All type。
3. `[筛选]` 各游戏厂商；是否支持多选需要实际验证。
4. `[按钮]` Reset。
5. `[按钮]` Confirm；提交后更新游戏列表。

### 游戏排序弹窗（Sort By）

截图：[`game-sort.png`](game-sort.png)

登录要求：与游戏主页一致。

1. `[按钮]` 关闭弹窗。
2. `[筛选]` Popular。
3. `[筛选]` Newest。
4. `[筛选]` A-Z。
5. `[筛选]` Z-A。
6. `[状态]` 截图中没有 Confirm，需验证是否选择后立即生效。

### VIP 中心

截图：[`vip-center.png`](vip-center.png)

登录要求：需要登录；游客从侧边栏进入时的行为待验证。

1. `[展示]` 当前 VIP 等级。
2. `[展示]` Upgrade Progress / 升级进度。
3. `[展示]` Retention Progress / 保级进度。
4. `[按钮]` 升级和保级规则说明。
5. `[展示]` Lucky 7 签到周期、日期和奖励状态。
6. `[按钮]` Lucky 7 说明。
7. `[按钮]` Check In、Checked In 或补签；按当前状态分别验证。
8. `[列表]` VIP Benefits 横向礼遇列表。
9. `[卡片]` Level Up Bonus、Birthday Bonus、Daily Cashback 等礼遇。
10. `[按钮]` 单项礼遇说明。
11. `[状态]` 横向滑动后的其他礼遇和分页位置。

## 已发现但缺少截图的下级页面

以下入口已经出现在当前截图中，但本目录尚无对应页面截图。后续如需全量客户端接口资产，应逐页补充，而不是只扫描入口：

- Forgot Password；
- SMS OTP 登录状态；
- 个人资料详情、站内信和通知；
- KYC 验证；
- Deposit、Withdraw；
- Transaction、Bet History、Bonus、Account；
- 活动详情、签到奖励详情、Filcoin 明细；
- FAQ；
- 商品详情、兑换确认和兑换记录；
- 游戏搜索、游戏启动和登录拦截；
- VIP 礼遇详情；
- 在线客服和 APP 下载的外部跳转。

## 待确认事项

1. “好友邀请已取消”是否等同于截图中的代理申请入口也应取消。
2. Earn Filcoins 页面是否另有“活动指南”入口；当前截图只明确看到 FAQ。
3. Rewards 和 VIP Center 中的 Lucky 7 是否复用同一活动和同一组接口。
4. Game Providers 是否支持多选，以及 Reset、Confirm 是否都会发请求。
5. Sort By 是否选择后立即生效。
6. 商品兑换动作位于商品卡片还是商品详情页。
7. 首页 Daily Rewards 的奖励是否可直接领取，还是只展示自动发放状态。
