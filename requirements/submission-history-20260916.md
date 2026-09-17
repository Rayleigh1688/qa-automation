# 班车需求提测时间核对：2026-09-16

[班车状态](status.md) · [需求入口](README.md)

来源：2026-09-16实时读取14个Story及其42个直属子任务的Jira changelog；56张工单返回的histories条数均等于total，无分页遗漏。仅保存状态变更字段、时间与历史ID，不保存用户账号、邮件或正文。时间统一为UTC+8。

口径：转入「FAT 测试」的状态记录作为本表的提测时间依据；它是Jira登记时间，不保证等于实际部署或群通知时间。开发、前端、App和QA分别列出；QA进入FAT不替代开发提测。直接Done/已完成、UAT或验收通过不能反推FAT时间。再次进入FAT保留全部节点，不自动认定为新版本部署。

本次只读核对，不执行测试或修改Jira，不解除既有暂停及测试范围约定。9月15日班车表是日期快照；本表刷新Jira状态，不代表重新核对了班车页面或部署。

## Story当前状态与子任务提测

| Story | 需求 | Jira当前状态 | 子任务进入FAT时间（全部节点） |
| --- | --- | --- | --- |
| [ISOP-2022](https://alibaba-international.atlassian.net/browse/ISOP-2022) | 管理後台 - 統計數據時間調整 | UAT 验收 | [ISOP-2044](https://alibaba-international.atlassian.net/browse/ISOP-2044) [後端] 2026-09-15 13:24:15<br>[ISOP-2045](https://alibaba-international.atlassian.net/browse/ISOP-2045) [前端] 2026-09-16 10:04:43<br>[ISOP-2046](https://alibaba-international.atlassian.net/browse/ISOP-2046) [QA] 2026-09-14 13:56:52<br>[ISOP-2085](https://alibaba-international.atlassian.net/browse/ISOP-2085) [後端] 2026-09-09 19:05:07 |
| [ISOP-2027](https://alibaba-international.atlassian.net/browse/ISOP-2027) | 管理後台 - KYC 複核功能 | 待上线 | [ISOP-2051](https://alibaba-international.atlassian.net/browse/ISOP-2051) [前端] 2026-09-09 17:31:41<br>[ISOP-2052](https://alibaba-international.atlassian.net/browse/ISOP-2052) [QA] 2026-09-11 10:07:06 |
| [ISOP-2028](https://alibaba-international.atlassian.net/browse/ISOP-2028) | 合規後台 - 統計數據時間調整 | FAT 测试 | [ISOP-2047](https://alibaba-international.atlassian.net/browse/ISOP-2047) [後端] 2026-09-15 13:24:13<br>[ISOP-2049](https://alibaba-international.atlassian.net/browse/ISOP-2049) [QA] 2026-09-16 10:06:56 |
| [ISOP-2029](https://alibaba-international.atlassian.net/browse/ISOP-2029) | 用戶端 - 免費旋轉領取文案調整 | 待上线 | [ISOP-2056](https://alibaba-international.atlassian.net/browse/ISOP-2056) [前端] 2026-09-07 14:24:23<br>[ISOP-2057](https://alibaba-international.atlassian.net/browse/ISOP-2057) [App] 2026-09-07 13:43:17<br>[ISOP-2058](https://alibaba-international.atlassian.net/browse/ISOP-2058) [QA] 2026-09-07 15:58:40 |
| [ISOP-2030](https://alibaba-international.atlassian.net/browse/ISOP-2030) | 用戶端 - 遊戲頁面改版 | 待上线 | [ISOP-2053](https://alibaba-international.atlassian.net/browse/ISOP-2053) [前端] 2026-09-10 10:17:04<br>[ISOP-2054](https://alibaba-international.atlassian.net/browse/ISOP-2054) [App] 2026-09-09 17:31:05<br>[ISOP-2055](https://alibaba-international.atlassian.net/browse/ISOP-2055) [QA] 2026-09-10 10:58:29 |
| [ISOP-2031](https://alibaba-international.atlassian.net/browse/ISOP-2031) | 新增金額動畫效果 | UAT 验收 | [ISOP-2080](https://alibaba-international.atlassian.net/browse/ISOP-2080) [後端] 2026-09-14 09:58:53<br>[ISOP-2081](https://alibaba-international.atlassian.net/browse/ISOP-2081) [前端] 2026-09-14 10:02:15<br>[ISOP-2082](https://alibaba-international.atlassian.net/browse/ISOP-2082) [App] 2026-09-14 10:36:50 |
| [ISOP-2032](https://alibaba-international.atlassian.net/browse/ISOP-2032) | 投注返利活動 | FAT 测试 | [ISOP-2075](https://alibaba-international.atlassian.net/browse/ISOP-2075) [後端] 2026-09-11 10:33:54<br>[ISOP-2076](https://alibaba-international.atlassian.net/browse/ISOP-2076) [後端] 2026-09-11 10:33:38<br>[ISOP-2078](https://alibaba-international.atlassian.net/browse/ISOP-2078) [前端] 2026-09-14 10:02:18<br>[ISOP-2078](https://alibaba-international.atlassian.net/browse/ISOP-2078) [前端] 2026-09-14 12:58:21<br>[ISOP-2079](https://alibaba-international.atlassian.net/browse/ISOP-2079) [App] 2026-09-15 11:02:05<br>[ISOP-2084](https://alibaba-international.atlassian.net/browse/ISOP-2084) [QA] 2026-09-16 10:06:50 |
| [ISOP-2037](https://alibaba-international.atlassian.net/browse/ISOP-2037) | 合規後台 - 全平台投注紀錄增加欄位 | 待上线 | [ISOP-2059](https://alibaba-international.atlassian.net/browse/ISOP-2059) [後端] 2026-09-08 16:23:44 |
| [ISOP-2038](https://alibaba-international.atlassian.net/browse/ISOP-2038) | 合規後台 - 移除 Jackpot 記錄選單 | 待上线 | [ISOP-2068](https://alibaba-international.atlassian.net/browse/ISOP-2068) [QA] 2026-09-08 13:23:00 |
| [ISOP-2041](https://alibaba-international.atlassian.net/browse/ISOP-2041) | JP 注單寫入方式調整 | 已完成 | [ISOP-2062](https://alibaba-international.atlassian.net/browse/ISOP-2062) [後端] 2026-09-07 14:51:05 |
| [ISOP-2043](https://alibaba-international.atlassian.net/browse/ISOP-2043) | 管理後台 - 新增 JP 資訊 | FAT 测试 | [ISOP-2064](https://alibaba-international.atlassian.net/browse/ISOP-2064) [後端] 2026-09-14 16:02:07<br>[ISOP-2065](https://alibaba-international.atlassian.net/browse/ISOP-2065) [前端] 2026-09-11 09:56:46<br>[ISOP-2066](https://alibaba-international.atlassian.net/browse/ISOP-2066) [QA] 2026-09-11 10:05:51 |
| [ISOP-2072](https://alibaba-international.atlassian.net/browse/ISOP-2072) | 報表數據更改爲排程計算 | 待办 | 子任务无FAT流转记录 |
| [ISOP-2086](https://alibaba-international.atlassian.net/browse/ISOP-2086) | 修改 Nav 的 Reward 為 Promos | 待上线 | [ISOP-2087](https://alibaba-international.atlassian.net/browse/ISOP-2087) [前端] 2026-09-14 12:58:24<br>[ISOP-2088](https://alibaba-international.atlassian.net/browse/ISOP-2088) [App] 2026-09-10 18:59:07 |
| [ISOP-2110](https://alibaba-international.atlassian.net/browse/ISOP-2110) | 編輯彈窗檢查邏輯調整 | 验收通过 | 无子任务；Story也无FAT流转记录 |

## 需要保留的差异

- 2032：客户端前端2078在9月14日10:02:18进入FAT，10:37:48退回进行中，12:58:21再次进入FAT；9月16日10:03:51进入UAT。App2079在9月15日11:02:05进入FAT。历史「客户端未提测」不能继续作为当前Jira状态结论，但本次不自动扩大执行授权。
- 2028：后端2047在9月15日13:24:13进入FAT，Story在9月16日10:13:00进入FAT。
- 2043：后端2064在9月14日16:02:07进入FAT，9月15日16:18:04退回进行中；前端2065在9月11日先进入UAT，再进入FAT，5秒后退回进行中，9月14日转Done。QA也存在短暂进入FAT后退回记录，不据此推断业务测试完成。
- 2022：Story及2044/2045/2046/2085现为UAT；既有问题和暂停不会被状态流转自动解除。
- 2030：Story在9月16日14:15:01由審查失敗转为待上线。
- 2072：两个子任务均待办，没有状态变更记录。2110没有子任务，Story仅在9月14日21:56:16由待办直接进入验收通过，无FAT提测时间依据。

## 完整状态时间线

下表包含全部状态变更（按时间正序）；括号内为Jira changelog历史ID，可与工单活动历史核对。Done保留历史原文，当前状态沿用Jira当前显示名称。

| Story / 工单 | 类型及标题 | 当前状态 | 全部状态修改节点（UTC+8；历史ID） |
| --- | --- | --- | --- |
| [ISOP-2022](https://alibaba-international.atlassian.net/browse/ISOP-2022) | Story：管理後台 - 統計數據時間調整 | UAT 验收 | 2026-09-14 13:57:03 待办 → 開發中（93723）<br>2026-09-14 13:57:05 開發中 → FAT 测试（93724）<br>2026-09-16 10:15:15 FAT 测试 → UAT 验收（94025） |
| ISOP-2022 / [ISOP-2044](https://alibaba-international.atlassian.net/browse/ISOP-2044) | [後端] 管理後台 - 統計數據時間調整 | UAT 验收 | 2026-09-14 09:59:57 待办 → 进行中（93683）<br>2026-09-15 13:24:15 进行中 → FAT 测试（93805）<br>2026-09-16 10:15:30 FAT 测试 → UAT 验收（94029） |
| ISOP-2022 / [ISOP-2045](https://alibaba-international.atlassian.net/browse/ISOP-2045) | [前端] 管理後台 - 統計數據時間調整 | UAT 验收 | 2026-09-08 10:06:24 待办 → 进行中（93353）<br>2026-09-16 10:04:43 进行中 → FAT 测试（94009）<br>2026-09-16 10:15:28 FAT 测试 → UAT 验收（94028） |
| ISOP-2022 / [ISOP-2046](https://alibaba-international.atlassian.net/browse/ISOP-2046) | [QA] 管理後台 - 統計數據時間調整 | UAT 验收 | 2026-09-14 13:56:44 待办 → 进行中（93721）<br>2026-09-14 13:56:52 进行中 → FAT 测试（93722）<br>2026-09-16 10:15:26 FAT 测试 → UAT 验收（94027） |
| ISOP-2022 / [ISOP-2085](https://alibaba-international.atlassian.net/browse/ISOP-2085) | [後端] 管理後台 - API 參數調整 | UAT 验收 | 2026-09-08 14:24:49 待办 → 进行中（93415）<br>2026-09-09 19:05:07 进行中 → FAT 测试（93539）<br>2026-09-16 10:15:22 FAT 测试 → UAT 验收（94026） |
| ISOP-2022 / [ISOP-2101](https://alibaba-international.atlassian.net/browse/ISOP-2101) | [前端] 管理後台 - API 參數調整 | 已完成 | 2026-09-11 10:12:26 待办 → 进行中（93615）<br>2026-09-11 10:13:58 进行中 → Done（93616） |
| [ISOP-2027](https://alibaba-international.atlassian.net/browse/ISOP-2027) | Story：管理後台 - KYC 複核功能 | 待上线 | 2026-09-11 10:06:53 待办 → 開發中（93611）<br>2026-09-11 10:06:55 開發中 → FAT 测试（93612）<br>2026-09-14 16:54:22 FAT 测试 → UAT 验收（93759）<br>2026-09-14 16:54:24 UAT 验收 → 審查失敗（93760）<br>2026-09-14 21:56:24 審查失敗 → 待上线（93776） |
| ISOP-2027 / [ISOP-2050](https://alibaba-international.atlassian.net/browse/ISOP-2050) | [後端] 管理後台 - KYC 複核功能 | 已完成 | 2026-09-08 10:04:12 待办 → 进行中（93348）<br>2026-09-09 16:09:54 进行中 → Done（93495） |
| ISOP-2027 / [ISOP-2051](https://alibaba-international.atlassian.net/browse/ISOP-2051) | [前端] 管理後台 - KYC 複核功能 | FAT 测试 | 2026-09-08 11:06:28 待办 → 进行中（93394）<br>2026-09-09 17:31:41 进行中 → FAT 测试（93538） |
| ISOP-2027 / [ISOP-2052](https://alibaba-international.atlassian.net/browse/ISOP-2052) | [QA] 管理後台 - KYC 複核功能 | 验收通过 | 2026-09-11 10:07:00 待办 → 进行中（93613）<br>2026-09-11 10:07:06 进行中 → FAT 测试（93614）<br>2026-09-14 13:18:31 FAT 测试 → Code Review（93720）<br>2026-09-16 10:05:38 Code Review → UAT 验收（94010）<br>2026-09-16 10:05:39 UAT 验收 → 验收通过（94011） |
| [ISOP-2028](https://alibaba-international.atlassian.net/browse/ISOP-2028) | Story：合規後台 - 統計數據時間調整 | FAT 测试 | 2026-09-16 10:12:53 待办 → 開發中（94023）<br>2026-09-16 10:13:00 開發中 → FAT 测试（94024） |
| ISOP-2028 / [ISOP-2047](https://alibaba-international.atlassian.net/browse/ISOP-2047) | [後端] 合規後台 - 統計數據時間調整 | FAT 测试 | 2026-09-11 16:56:16 待办 → 进行中（93644）<br>2026-09-15 13:24:13 进行中 → FAT 测试（93804） |
| ISOP-2028 / [ISOP-2048](https://alibaba-international.atlassian.net/browse/ISOP-2048) | [前端] 合規後台 - 統計數據時間調整 | 已完成 | 2026-09-11 16:59:44 待办 → 进行中（93650）<br>2026-09-15 13:19:53 进行中 → Done（93803） |
| ISOP-2028 / [ISOP-2049](https://alibaba-international.atlassian.net/browse/ISOP-2049) | [QA] 合規後台 - 統計數據時間調整 | FAT 测试 | 2026-09-16 10:06:55 待办 → 进行中（94014）<br>2026-09-16 10:06:56 进行中 → FAT 测试（94015） |
| [ISOP-2029](https://alibaba-international.atlassian.net/browse/ISOP-2029) | Story：用戶端 - 免費旋轉領取文案調整 | 待上线 | 2026-09-07 13:42:39 待办 → 開發中（93258）<br>2026-09-07 13:42:43 開發中 → FAT 测试（93259）<br>2026-09-07 16:00:21 FAT 测试 → UAT 验收（93276）<br>2026-09-09 12:06:34 UAT 验收 → 待上线（93443） |
| ISOP-2029 / [ISOP-2056](https://alibaba-international.atlassian.net/browse/ISOP-2056) | [前端] 用戶端 - 免費旋轉領取文案調整 | 验收通过 | 2026-09-07 14:24:19 待办 → 进行中（93267）<br>2026-09-07 14:24:23 进行中 → FAT 测试（93268）<br>2026-09-08 10:05:35 FAT 测试 → UAT 验收（93352）<br>2026-09-09 12:06:38 UAT 验收 → 验收通过（93444） |
| ISOP-2029 / [ISOP-2057](https://alibaba-international.atlassian.net/browse/ISOP-2057) | [App] 用戶端 - 免費旋轉領取文案調整 | 验收通过 | 2026-09-07 13:43:14 待办 → 进行中（93260）<br>2026-09-07 13:43:17 进行中 → FAT 测试（93261）<br>2026-09-08 10:06:57 FAT 测试 → UAT 验收（93354）<br>2026-09-09 12:06:39 UAT 验收 → 验收通过（93445） |
| ISOP-2029 / [ISOP-2058](https://alibaba-international.atlassian.net/browse/ISOP-2058) | [QA] 用戶端 - 免費旋轉領取文案調整 | 验收通过 | 2026-09-07 15:58:33 待办 → 进行中（93273）<br>2026-09-07 15:58:40 进行中 → FAT 测试（93274）<br>2026-09-07 15:58:43 FAT 测试 → UAT 验收（93275）<br>2026-09-09 12:06:42 UAT 验收 → 验收通过（93446） |
| [ISOP-2030](https://alibaba-international.atlassian.net/browse/ISOP-2030) | Story：用戶端 - 遊戲頁面改版 | 待上线 | 2026-09-10 10:58:32 待办 → 開發中（93561）<br>2026-09-10 10:58:35 開發中 → FAT 测试（93562）<br>2026-09-10 15:20:43 FAT 测试 → UAT 验收（93583）<br>2026-09-10 23:10:32 UAT 验收 → 審查失敗（93590）<br>2026-09-16 14:15:01 審查失敗 → 待上线（94055） |
| ISOP-2030 / [ISOP-2053](https://alibaba-international.atlassian.net/browse/ISOP-2053) | [前端] 用戶端 - 遊戲頁面改版 | 验收通过 | 2026-09-09 10:06:06 待办 → 进行中（93436）<br>2026-09-10 10:17:04 进行中 → FAT 测试（93551）<br>2026-09-15 10:03:42 FAT 测试 → UAT 验收（93785）<br>2026-09-16 14:14:49 UAT 验收 → 验收通过（94051） |
| ISOP-2030 / [ISOP-2054](https://alibaba-international.atlassian.net/browse/ISOP-2054) | [App] 用戶端 - 遊戲頁面改版 | 验收通过 | 2026-09-07 14:08:51 待办 → 进行中（93263）<br>2026-09-09 17:31:05 进行中 → FAT 测试（93537）<br>2026-09-15 10:05:45 FAT 测试 → UAT 验收（93786）<br>2026-09-16 14:14:51 UAT 验收 → 验收通过（94052） |
| ISOP-2030 / [ISOP-2055](https://alibaba-international.atlassian.net/browse/ISOP-2055) | [QA] 用戶端 - 遊戲頁面改版 | 验收通过 | 2026-09-10 10:58:27 待办 → 进行中（93559）<br>2026-09-10 10:58:29 进行中 → FAT 测试（93560）<br>2026-09-10 15:20:41 FAT 测试 → UAT 验收（93582）<br>2026-09-16 14:14:52 UAT 验收 → 验收通过（94054） |
| [ISOP-2031](https://alibaba-international.atlassian.net/browse/ISOP-2031) | Story：新增金額動畫效果 | UAT 验收 | 2026-09-16 10:11:52 待办 → 開發中（94016）<br>2026-09-16 10:12:00 開發中 → FAT 测试（94017）<br>2026-09-16 10:12:03 FAT 测试 → UAT 验收（94018） |
| ISOP-2031 / [ISOP-2080](https://alibaba-international.atlassian.net/browse/ISOP-2080) | [後端] 新增金額動畫效果 API、MQTT | FAT 测试 | 2026-09-14 09:58:51 待办 → 进行中（93681）<br>2026-09-14 09:58:53 进行中 → FAT 测试（93682） |
| ISOP-2031 / [ISOP-2081](https://alibaba-international.atlassian.net/browse/ISOP-2081) | [前端] 用戶端 - 新增金額動畫效果 | UAT 验收 | 2026-09-08 13:33:57 待办 → 进行中（93408）<br>2026-09-14 10:02:15 进行中 → FAT 测试（93684）<br>2026-09-16 10:03:46 FAT 测试 → UAT 验收（94007） |
| ISOP-2031 / [ISOP-2082](https://alibaba-international.atlassian.net/browse/ISOP-2082) | [App] 用戶端 - 新增金額動畫效果 | FAT 测试 | 2026-09-09 14:43:58 待办 → 进行中（93449）<br>2026-09-14 10:36:50 进行中 → FAT 测试（93694） |
| ISOP-2031 / [ISOP-2083](https://alibaba-international.atlassian.net/browse/ISOP-2083) | [QA] 新增金額動畫效果 | 已完成 | 2026-09-15 10:07:22 待办 → UAT 验收（93788）<br>2026-09-16 10:12:13 UAT 验收 → 验收通过（94019）<br>2026-09-16 10:12:16 验收通过 → Done（94020） |
| [ISOP-2032](https://alibaba-international.atlassian.net/browse/ISOP-2032) | Story：投注返利活動 | FAT 测试 | 2026-09-16 10:12:24 待办 → 開發中（94021）<br>2026-09-16 10:12:26 開發中 → FAT 测试（94022） |
| ISOP-2032 / [ISOP-2075](https://alibaba-international.atlassian.net/browse/ISOP-2075) | [後端] 投注返利活動邏輯、後台 API | FAT 测试 | 2026-09-09 10:03:07 待办 → 进行中（93431）<br>2026-09-11 10:33:54 进行中 → FAT 测试（93618） |
| ISOP-2032 / [ISOP-2076](https://alibaba-international.atlassian.net/browse/ISOP-2076) | [後端] 投注返利活動用戶端需求 API / MQTT 訊息 | FAT 测试 | 2026-09-09 10:03:05 待办 → 进行中（93430）<br>2026-09-11 10:33:38 进行中 → FAT 测试（93617） |
| ISOP-2032 / [ISOP-2077](https://alibaba-international.atlassian.net/browse/ISOP-2077) | [前端] 管理後台 - 投注返利活動編輯、報表介面 | 已完成 | 2026-09-08 16:28:58 待办 → 进行中（93423）<br>2026-09-14 09:46:35 进行中 → Done（93670） |
| ISOP-2032 / [ISOP-2078](https://alibaba-international.atlassian.net/browse/ISOP-2078) | [前端] 用戶端 - 投注返利活動動畫效果、活動頁 | UAT 验收 | 2026-09-08 16:38:18 待办 → 进行中（93428）<br>2026-09-14 10:02:18 进行中 → FAT 测试（93685）<br>2026-09-14 10:37:48 FAT 测试 → 进行中（93695）<br>2026-09-14 12:58:21 进行中 → FAT 测试（93716）<br>2026-09-16 10:03:51 FAT 测试 → UAT 验收（94008） |
| ISOP-2032 / [ISOP-2079](https://alibaba-international.atlassian.net/browse/ISOP-2079) | [App] 用戶端 - 投注返利活動動畫效果、活動頁 | FAT 测试 | 2026-09-09 14:44:02 待办 → 进行中（93450）<br>2026-09-15 11:02:05 进行中 → FAT 测试（93791） |
| ISOP-2032 / [ISOP-2084](https://alibaba-international.atlassian.net/browse/ISOP-2084) | [QA] 投注返利活動 | FAT 测试 | 2026-09-16 10:06:48 待办 → 进行中（94012）<br>2026-09-16 10:06:50 进行中 → FAT 测试（94013） |
| [ISOP-2037](https://alibaba-international.atlassian.net/browse/ISOP-2037) | Story：合規後台 - 全平台投注紀錄增加欄位 | 待上线 | 2026-09-09 10:45:47 待办 → 開發中（93438）<br>2026-09-09 10:45:49 開發中 → FAT 测试（93439）<br>2026-09-11 10:06:29 FAT 测试 → UAT 验收（93609）<br>2026-09-14 13:17:53 UAT 验收 → 審查失敗（93718）<br>2026-09-14 13:17:59 審查失敗 → 待上线（93719） |
| ISOP-2037 / [ISOP-2059](https://alibaba-international.atlassian.net/browse/ISOP-2059) | [後端] 合規後台 - 全平台投注紀錄增加欄位 | UAT 验收 | 2026-09-08 11:41:52 待办 → 进行中（93396）<br>2026-09-08 16:23:44 进行中 → FAT 测试（93420）<br>2026-09-09 17:22:19 FAT 测试 → UAT 验收（93534） |
| ISOP-2037 / [ISOP-2060](https://alibaba-international.atlassian.net/browse/ISOP-2060) | [前端] 合規後台 - 全平台投注紀錄增加欄位 | 已完成 | 2026-09-08 16:52:06 待办 → 进行中（93429）<br>2026-09-09 10:04:11 进行中 → Done（93435） |
| ISOP-2037 / [ISOP-2061](https://alibaba-international.atlassian.net/browse/ISOP-2061) | [QA] 合規後台 - 全平台投注紀錄增加欄位 | 已完成 | 2026-09-09 10:45:45 待办 → 进行中（93437）<br>2026-09-11 10:06:26 进行中 → Done（93608） |
| [ISOP-2038](https://alibaba-international.atlassian.net/browse/ISOP-2038) | Story：合規後台 - 移除 Jackpot 記錄選單 | 待上线 | 2026-09-08 13:19:04 待办 → 開發中（93400）<br>2026-09-08 13:19:06 開發中 → FAT 测试（93401）<br>2026-09-10 23:12:37 FAT 测试 → 開發中（93592）<br>2026-09-10 23:12:38 開發中 → FAT 测试（93593）<br>2026-09-10 23:12:41 FAT 测试 → UAT 验收（93594）<br>2026-09-10 23:12:43 UAT 验收 → 待上线（93595） |
| ISOP-2038 / [ISOP-2067](https://alibaba-international.atlassian.net/browse/ISOP-2067) | [前端] 合規後台 - 移除 Jackpot 記錄選單 | 已完成 | 2026-09-08 13:14:01 待办 → 进行中（93397）<br>2026-09-08 13:18:10 进行中 → Done（93398） |
| ISOP-2038 / [ISOP-2068](https://alibaba-international.atlassian.net/browse/ISOP-2068) | [QA] 合規後台 - 移除 Jackpot 記錄選單 | 已完成 | 2026-09-08 13:18:59 待办 → 进行中（93399）<br>2026-09-08 13:23:00 进行中 → FAT 测试（93402）<br>2026-09-10 23:12:33 FAT 测试 → UAT 验收（93591）<br>2026-09-10 23:12:47 UAT 验收 → 验收通过（93596）<br>2026-09-10 23:12:51 验收通过 → Done（93597） |
| [ISOP-2041](https://alibaba-international.atlassian.net/browse/ISOP-2041) | Story：JP 注單寫入方式調整 | 已完成 | 2026-09-09 15:00:34 待办 → 開發中（93464）<br>2026-09-09 15:00:35 開發中 → FAT 测试（93465）<br>2026-09-09 15:00:38 FAT 测试 → UAT 验收（93466）<br>2026-09-09 15:00:41 UAT 验收 → 待上线（93467）<br>2026-09-09 15:00:42 待上线 → Done（93468） |
| ISOP-2041 / [ISOP-2062](https://alibaba-international.atlassian.net/browse/ISOP-2062) | [後端] JP 注單寫入方式調整 | 已完成 | 2026-09-07 14:26:07 待办 → 进行中（93270）<br>2026-09-07 14:51:05 进行中 → FAT 测试（93271）<br>2026-09-09 15:00:21 FAT 测试 → UAT 验收（93459）<br>2026-09-09 15:00:24 UAT 验收 → 验收通过（93460）<br>2026-09-09 15:00:28 验收通过 → Done（93462）<br>2026-09-09 17:22:41 Done → UAT 验收（93536）<br>2026-09-16 09:53:58 UAT 验收 → 验收通过（94002）<br>2026-09-16 09:54:01 验收通过 → Done（94003） |
| ISOP-2041 / [ISOP-2063](https://alibaba-international.atlassian.net/browse/ISOP-2063) | [QA] JP 注單寫入方式調整 | 已完成 | 2026-09-09 15:00:17 待办 → UAT 验收（93458）<br>2026-09-09 15:00:26 UAT 验收 → 验收通过（93461）<br>2026-09-09 15:00:30 验收通过 → Done（93463） |
| [ISOP-2043](https://alibaba-international.atlassian.net/browse/ISOP-2043) | Story：管理後台 - 新增 JP 資訊 | FAT 测试 | 2026-09-16 09:50:19 待办 → 開發中（94000）<br>2026-09-16 09:50:20 開發中 → FAT 测试（94001） |
| ISOP-2043 / [ISOP-2064](https://alibaba-international.atlassian.net/browse/ISOP-2064) | [後端] 管理後台 - 新增 JP 資訊 | 进行中 | 2026-09-10 10:02:10 待办 → 进行中（93540）<br>2026-09-14 16:02:07 进行中 → FAT 测试（93741）<br>2026-09-15 16:18:04 FAT 测试 → 进行中（93881） |
| ISOP-2043 / [ISOP-2065](https://alibaba-international.atlassian.net/browse/ISOP-2065) | [前端] 管理後台 - 新增 JP 資訊 | 已完成 | 2026-09-11 09:52:34 待办 → UAT 验收（93599）<br>2026-09-11 09:56:46 UAT 验收 → FAT 测试（93600）<br>2026-09-11 09:56:51 FAT 测试 → 进行中（93601）<br>2026-09-14 09:48:39 进行中 → Done（93680） |
| ISOP-2043 / [ISOP-2066](https://alibaba-international.atlassian.net/browse/ISOP-2066) | [QA] 【冒烟测试】 - 新增 JP 資訊 | 进行中 | 2026-09-10 10:05:41 待办 → 进行中（93543）<br>2026-09-11 10:05:51 进行中 → FAT 测试（93602）<br>2026-09-11 10:05:57 FAT 测试 → 进行中（93603） |
| [ISOP-2072](https://alibaba-international.atlassian.net/browse/ISOP-2072) | Story：報表數據更改爲排程計算 | 待办 | 无状态变更记录 |
| ISOP-2072 / [ISOP-2073](https://alibaba-international.atlassian.net/browse/ISOP-2073) | [後端] 報表數據更改爲排程計算 | 待办 | 无状态变更记录 |
| ISOP-2072 / [ISOP-2074](https://alibaba-international.atlassian.net/browse/ISOP-2074) | [QA] 報表數據更改爲排程計算 | 待办 | 无状态变更记录 |
| [ISOP-2086](https://alibaba-international.atlassian.net/browse/ISOP-2086) | Story：修改 Nav 的 Reward 為 Promos | 待上线 | 2026-09-14 11:11:38 待办 → 開發中（93711）<br>2026-09-14 11:11:40 開發中 → FAT 测试（93712）<br>2026-09-15 10:57:44 FAT 测试 → UAT 验收（93789）<br>2026-09-15 11:45:02 UAT 验收 → 待上线（93797） |
| ISOP-2086 / [ISOP-2087](https://alibaba-international.atlassian.net/browse/ISOP-2087) | [前端] 用戶端 - 修改 Nav 的 Reward 為 Promos | 验收通过 | 2026-09-14 10:27:15 待办 → 进行中（93693）<br>2026-09-14 12:58:24 进行中 → FAT 测试（93717）<br>2026-09-15 11:45:08 FAT 测试 → UAT 验收（93798）<br>2026-09-15 11:45:12 UAT 验收 → 验收通过（93799） |
| ISOP-2086 / [ISOP-2088](https://alibaba-international.atlassian.net/browse/ISOP-2088) | [App] 用戶端 - 修改 Nav 的 Reward 為 Promos | 验收通过 | 2026-09-10 18:59:04 待办 → 进行中（93586）<br>2026-09-10 18:59:07 进行中 → FAT 测试（93587）<br>2026-09-15 11:45:14 FAT 测试 → UAT 验收（93800）<br>2026-09-15 11:45:17 UAT 验收 → 验收通过（93801） |
| ISOP-2086 / [ISOP-2096](https://alibaba-international.atlassian.net/browse/ISOP-2096) | [QA] 用戶端 - 修改 Nav 的 Reward 為 Promos | 验收通过 | 2026-09-14 16:40:17 待办 → UAT 验收（93758）<br>2026-09-15 11:45:18 UAT 验收 → 验收通过（93802） |
| [ISOP-2110](https://alibaba-international.atlassian.net/browse/ISOP-2110) | Story：編輯彈窗檢查邏輯調整 | 验收通过 | 2026-09-14 21:56:16 待办 → 验收通过（93775） |

核对边界：本次不读取业务结果来替代提测历史，不以父Story状态覆盖子任务差异；未重跑API/UI，未刷新关联需求正文、评论、Lark或班车页面。

