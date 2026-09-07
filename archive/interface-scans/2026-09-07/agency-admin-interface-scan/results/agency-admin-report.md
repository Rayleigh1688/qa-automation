# FAT 代理管理后台接口发现报告

- 登录门禁：PASS；实际域名 `https://admin-agency-fat.filbet2025.com`，登录后路由 `/home`；`POST /backend/agency/login` 与 `GET /backend/agency/me/detail` 均为 HTTP 200 / business true，渲染 11 个菜单叶子。
- 菜单/路由：11 个菜单叶子，11 个真实路由；尝试 11 页，有效扫描 11 页，阻塞 0 页，未尝试 0 页。
- DOM 控件：359 条；操作结论：71 条；动作类型 {'query': 9, 'reset': 9, 'tab': 15, 'chart_mode': 2, 'chart_mode_restore': 1, 'chart_series_legend': 1, 'details': 1, 'filter_query': 8, 'filter_reset': 8, 'filter_select_options': 13, 'pagination_next': 2, 'pagination_restore': 2}；动作状态 {'CLICKED': 43, 'RESTORED': 11, 'BLOCKED_PREREQUISITE': 1, 'OPENED_AND_CLOSED': 13, 'INTERACTION_ERROR': 3}。3 个 `filter_query` 在先前 Query 导致表单重绘后 locator 失效，已按 `INTERACTION_ERROR` 原样保留；对应页面的常规 Query/Reset 已成功，不虚报这 3 次过滤输入。
- Network：62 条，18 个唯一 method+path；动态分类 {'ACTIVE': 16, 'UNDOCUMENTED_ACTIVE': 1, 'MISCLASSIFIED': 1}。只使用仓库规定的九种最终状态；未观察文档接口没有判为 `STALE`。
- 覆盖了页面初始化、DOM 控件、查询/重置、可逆文本过滤、筛选下拉选项、分页前进并恢复、详情弹层、页签和首页图表模式。未发现可安全触发的导出、抽屉或 Overflow 控件；这些缺口以 DOM 实况保留，不推断接口状态。
- `Line Chart Mode` / `Bar Chart Mode` 是纯本地展示切换，没有 Network，最终恢复初始 Bar。语义不明确的 `On / Closed` switch 未点击，记录为 `BLOCKED_PREREQUISITE`。
- 持久写仅允许当前轮自建目标并具备明确恢复路径；本轮没有符合条件的目标，写操作为 0。
- 页面门禁：每页都要求实际 origin、pathname 和已认证侧栏同时成立；任何 `/user/login` 重定向均计为阻塞并立即停止，不会虚报已扫描。
- 边界：最终轮只启动一个全新 Playwright context 并登录一次；未复用 Token/storage state；没有进入 UAT、Jenkins、数据库或共享 inventory/catalog/P0/P1。

## 已验证页面

  - `/home` — Home — `SCANNED`
  - `/agent/agent-review` — Agent Review — `SCANNED`
  - `/agent/agent-list` — Agent List — `SCANNED`
  - `/agent/user-list` — Member List — `SCANNED`
  - `/agent/agent-setting` — Agent Settings — `SCANNED`
  - `/agent/domain` — Agent Domain — `SCANNED`
  - `/financial/commission-review` — Commission Review — `SCANNED`
  - `/financial/commission-list` — Commission Report — `SCANNED`
  - `/financial/financial-statements` — Financial Report — `SCANNED`
  - `/system/role` — Role Configuration — `SCANNED`
  - `/system/staff` — Staff Configuration — `SCANNED`
