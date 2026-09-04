# FAT 代理前台接口发现报告

- 登录门禁：**PASS**；登录后实际 origin `https://agency-fat.filbet2025.com`，路由 `/`。登录请求与身份/Profile 请求均有成功证据。
- 会话隔离：扫描器创建全新专用 Playwright browser context，不加载或导出 storage state，不复用代理管理后台 Token。
- 当前账号已认证导航面：5 个菜单定义/可访问叶子，5 个解析路由；扫描 5 页，页面错误 0。
- 菜单证据说明：通用 `aside/nav` selector 未命中该站点的自定义/响应式导航壳（`navigation_shell_visible=false`），不据此判菜单缺失。5 个 bundle 导航候选均已由登录态下实际 pathname、页面控件和页面初始化 Network 动态核对成功；其中可识别的精确菜单文案另有 DOM 证据。
- DOM 与操作：47 条可见控件结构，30 条操作/可见性结论。已执行首页 Search/Reset、列表 Reset、筛选展开、规则页签和当前可见 Overflow；未点击的日期快捷项、`Search / Query`、复制/海报等控件逐项保留为 `VISIBLE_NOT_EXECUTED` / `DOCUMENTED_UNVERIFIED`。当前 DOM 未渲染分页、详情、导出或独立抽屉入口。
- Network：19 条首方事件，11 个唯一 method+path；动态分类 `{'ACTIVE': 11}`。
- 静态对照：只读取 inventory 中顶层 `代理后台` 的 20 个 method+path；没有混入 `代理管理后台`。未观察文档接口保持 `DOCUMENTED_UNVERIFIED`，没有仅凭缺失动态证据判 `STALE`。
- 写操作：0。当前账号不是本轮新建目标，未提交密码重置、消息发送、设置或资金相关持久写；不存在恢复遗留。
- 敏感信息：手机号、OTP、Token、Cookie、设备标识和响应业务值均未保留；结果只含字段名、类型、计数、标准化路径和脱敏 DOM 标签。
- 边界：仅 FAT；未进入 UAT、Jenkins、数据库、共享 inventory/catalog 或 P0/P1 资产。
