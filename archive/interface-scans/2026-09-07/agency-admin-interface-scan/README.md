# FAT 代理管理后台接口发现

本目录仅保存 `https://admin-agency-fat.filbet2025.com/` 的独立动态发现资产，不修改共享 `api/inventory/interfaces.csv`、`api/catalog/` 或 P0/P1 范围。

扫描器每次启动全新的 Playwright browser context，不读取或输出 storage state、Token、Cookie、设备 ID。登录凭据通过运行时环境变量传入；实时 TOTP 从根目录被忽略的二维码在内存生成，二维码内容、seed 和验证码不写入日志或结果。

结果位于 `results/`：菜单/路由、DOM 控件、操作证据、endpoint 分类、汇总和报告。静态对照只接受 inventory 中 `source_file` 顶层为“代理管理后台”的记录，避免把代理前台 `/agency/*` 静态文档误算为本轮动态覆盖。

动态最终分类只使用仓库规定的九种状态。未观察到的文档接口不判为 `STALE`。持久化写操作只有在目标由本轮创建且存在明确恢复路径时才允许执行。

## 本地运行

根目录需要存在被 Git 忽略的 `agency-admin-QR.png`，并安装可读取二维码的 `zbarimg`。凭据只通过当前进程环境变量传入：

```bash
AGENCY_ADMIN_EMAIL=<runtime-only> AGENCY_ADMIN_PASSWORD=<runtime-only> \
node agency-admin-interface-scan/agency-admin-scan.mjs
python3 agency-admin-interface-scan/build-results.py
```

需要观察浏览器时额外设置 `AGENCY_SCAN_HEADED=true`。运行结束后必须再次检查结果中不包含凭据、二维码内容、TOTP、Token、Cookie、设备 ID 或原始个人数据。

## 最新有效轮次

2026-09-03 最终轮只创建一个全新 Playwright context 并登录一次。登录门禁同时验证 `POST /backend/agency/login`、`GET /backend/agency/me/detail`、实际 origin、登录后 route 和渲染菜单；随后 11 个菜单路由逐页通过实际 pathname 与已认证侧栏硬门禁。结果为 11/11 有效页面、0 页面错误、359 条 DOM 控件、71 条安全或可逆动作结论、62 条首方 Network 事件和 18 个唯一 method+path。持久写操作为 0，`fatal_error` 为空；详情弹层中的测试账号已脱敏。

3 次额外的可逆文本过滤在常规 Query 触发表单重绘后 locator 失效，明确记录为 `INTERACTION_ERROR`；对应页面的常规 Query/Reset 已成功。这些错误不被改写成接口成功，也不影响 11 个页面初始化、路由、DOM 和 Network 主门禁结论。
