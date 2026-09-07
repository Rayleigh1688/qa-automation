# CI 接入状态

当前 Jenkins 配置尚未随最新本地入口完成联网验收，不能把本地 PASS 当成 CI 已验证。

恢复 CI 工作时需要先处理：

- `Jenkinsfile` 全局固定后台登录码与 UAT 动态 TOTP 规则不一致。
- 按环境注入认证变量并核验 env 文件与 URL/scope 的一致性。
- 将 `npm run check` 加入独立工程校验阶段。
- 验证失败归档和 `api/results/operations/` 嵌套产物，检查归档中的敏感信息。
- `api_all` 实际仅 safe/negative；`api_write` 实际调用 API+UI full，应在后续 CI 改造中澄清参数命名。

环境凭据 schema 见 [环境手册](../api/runbooks/ENVIRONMENTS.md) 和 [配置模板](../.env.example)。不得直接照搬 FAT 认证变量用于 UAT。

## 现有配置参考（未验收）


[Jenkinsfile](../Jenkinsfile) 当前声明以下参数：

| 参数 | 推荐值 | 用途 |
| --- | --- | --- |
| `TARGET_ENV` | `fat` / `uat` | `fat` 用于发布 UAT 前测试环境验证，`uat` 用于发布 UAT 后验证 |
| `P0_SCOPE` | `api_all` | 执行 API 只读正例和默认安全反例；不创建测试订单 |
| `EXECUTE_BET` | `false` | 默认不做真实投注点击 |

待验收的调用流程：

1. 发布 UAT 前，在测试环境执行：`TARGET_ENV=fat`、`P0_SCOPE=api_all`。
2. 发布 UAT 后，在 UAT 执行：`TARGET_ENV=uat`、`P0_SCOPE=api_all`。
3. UI 自动化作为补充检查，需要同时验证安全 API 检查与前端时执行 `P0_SCOPE=api_and_ui`；只执行 UI 时使用 `ui_only`。
4. 涉及注册、充值、提现和审核链路验证时，人工触发 `P0_SCOPE=api_write`。该 scope 执行完整受控主流程，必须确认测试账号、活动流水、审核令牌和资金影响可控。

## 验收要求

凭据变量以环境手册和 `.env.example` 为准，认证必须按 FAT/UAT 分开配置。联网恢复后分别验证成功与受控失败、退出码、报告归档、脱敏及流水线参数实际行为；在这些检查完成前，不声明 CI 门禁已经可用。
