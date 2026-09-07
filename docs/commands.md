# 高级命令与执行范围

日常只跑 API P0 和默认 UI P0 时，直接使用 [README 的两个入口](../README.md#日常-p0-测试两个入口)。本文件供组合资金链、专项和排障时查阅，无需日常逐条执行。

这里维护公开命令的语义；具体参数由 `package.json` 与脚本定义，环境契约见 [环境手册](../api/runbooks/ENVIRONMENTS.md)。

| 命令 | 执行范围 | 业务写入与证据边界 |
| --- | --- | --- |
| `npm run check` | 资产、文档、源码语法和本地单元测试 | 无业务请求 |
| `npm run test:p0:api:read` | safe API + 默认保护性反例 | 有认证请求，不创建资金订单；不包含已知会建单的充值限额探针 |
| `npm run test:ui:p0` | 固定默认 UI 清单 | 默认只验证页面/游戏启动；专项写入开关应保持关闭 |
| `npm run test:p0` | safe API/negative + 默认 UI | 快速组合门禁 |
| `npm run test:p0:api` | safe/negative + 新号注册、KYC、充值补单、后台清流、提款账户准备、提现及审核阶段 | 会写业务数据；纯 API，不证明三方投注；遇业务失败停止，不能保证最终出款 |
| `npm run test:p0:full` | 永久 BASIC UI 拦截、独立 KYC、safe/negative、默认 UI、充值、真实 UI 投注、流水及提现关联 | 会写业务数据；默认按剩余流水投注；后台清流由 `--clear-remaining-turnover` 显式启用 |

`test:api`、`test:api:write` 与 `test:p0:api` 调用同一个 API 入口；`test:p0:ui` 是默认 UI 别名。不要把 `test:api` 当成只读命令。

## 环境和参数

```bash
ENV_FILE=.env.fat npm run test:p0:api:read
ENV_FILE=.env.uat npm run test:ui:p0
python3 scripts/run-api-tests.py p0 --env .env.uat --scope UAT --safe-only
```

完整链路固定次数示例（包含资金写入）：

```bash
ENV_FILE=.env.fat npm run test:p0:full -- --bet-spins 10 --clear-remaining-turnover --deposit-amount 1200 --withdraw-amount 1000
```

Python UI/full 入口支持 `--headed`。固定次数模式分别记录投注后流水与后台清流后流水，不能声称流水全由投注完成。

单阶段注册、KYC、充值、提现、查询和审批命令见 [API 手册](../api/runbooks/API.md) 和 [P0 资产说明](../api/p0/README.md)；UI 专项开关见 [UI 手册](../ui/README.md)。查询/审批必须关联当前 flow 的明确 ID。

## 结果语义

- API 报告统计请求/断言，UI 报告统计固定用例，主流程报告统计八个业务场景，数量不能直接比较。
- 结构查询允许空页时，仅证明响应契约；订单关联必须证明本轮订单存在且字段匹配。
- `test:p0:api` 生成 API 报告；完整主流程报告由 `test:p0:full` 负责。
- 非零退出表示运行没有通过。既有 runner 的 `FAILED/BLOCKED` 表达不同失败阶段，诊断时同时查看阶段、退出码及原始错误。

## API / UI 可复制命令（FAT）

API 无资金写入（认证与默认保护性反例仍会发送请求）：

```bash
ENV_FILE=.env.fat npm run test:p0:api:read
```

API 受控写入组合（注册、KYC、充值补单、后台清流、账户准备、提现及审核阶段，不含真实 UI 投注）：

```bash
ENV_FILE=.env.fat npm run test:p0:api
```

UI 默认套件，明确关闭资金开关；`ENV_FILE_PRECEDENCE=shell` 防止本地配置覆盖显式开关：

```bash
ENV_FILE=.env.fat ENV_FILE_PRECEDENCE=shell EXECUTE_BET=false EXECUTE_DEPOSIT_CONTRACT=false EXECUTE_WITHDRAW_UI=false npm run test:ui:p0
```

UI 带写动作按专项执行，并非一个自动串联充值、投注和提现的 UI 总入口：

```bash
# 充值页面创建订单 1000，不等于后台补单或实际到账
ENV_FILE=.env.fat ENV_FILE_PRECEDENCE=shell EXECUTE_DEPOSIT_CONTRACT=true CLIENT_DEPOSIT_AMOUNT=1000 npm run test:ui:deposit-contract

# 游戏内真实投注 1 次；单注读取本地 CLIENT_GAME_BET_AMOUNT
ENV_FILE=.env.fat ENV_FILE_PRECEDENCE=shell EXECUTE_BET=true CLIENT_GAME_SPIN_COUNT=1 npm run test:ui:game-bet

# Maya 提现页面提交 1000；需已 KYC、余额/流水/提款账户满足前置及本地 CLIENT_WALLET_PASSWORD
ENV_FILE=.env.fat ENV_FILE_PRECEDENCE=shell EXECUTE_WITHDRAW_UI=true CLIENT_WITHDRAW_CHANNEL=Maya CLIENT_WITHDRAW_AMOUNT=1000 npm run test:ui:withdraw-contract
```

默认 10 条 UI 不提交提现；提现专项明确开启写开关才提交合法订单。以上专项各自清理 UI 最近结果，且不自动调用默认 UI 汇总渲染器；不能把专项结果当成默认 10 条套件已重跑。完整跨 API/UI 资金链使用本文件的 `test:p0:full`，其中提现由 API 创建。
