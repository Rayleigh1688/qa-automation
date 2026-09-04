# FAT 代理前台接口扫描

本目录是 `https://agency-fat.filbet2025.com/` 的独立接口发现资产，与 `agency-admin-interface-scan/` 完全分离。

- 扫描器每次创建全新 Playwright browser context，不读取或保存 storage state。
- 登录手机号和 OTP 只能用运行时环境变量注入；不得写入脚本、结果或日志。
- 结果只保存请求字段名、响应结构、标准化路径和脱敏 DOM 标签，不保存业务数据值。
- 静态对照仅使用 `api/inventory/interfaces.csv` 中 `top_domain=代理后台` 的记录。
- 当前角色未观察到的文档接口保持 `DOCUMENTED_UNVERIFIED`，不能仅凭未观察判为 `STALE`。
- 不执行非本轮自建数据的持久写操作，不进入 UAT、Jenkins 或数据库，不修改共享 inventory/catalog/P0/P1。

本地运行：

```bash
AGENCY_PORTAL_PHONE=<runtime-only> AGENCY_PORTAL_OTP=<runtime-only> \
node agency-portal-interface-scan/agency-portal-scan.mjs
python3 agency-portal-interface-scan/build-results.py
```

主要产物位于 [`results/`](results/)：登录门禁、菜单/路由、权限观察、DOM 控件、操作证据、动态 endpoint、静态对照、汇总和报告。
