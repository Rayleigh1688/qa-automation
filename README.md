# QA Automation

这是一个用于逐步建设测试自动化体系的工作区。

## 目录结构

```text
testing-plan/    测试自动化建设规划
skills/          测试方法、规范、业务规则沉淀
harness/         调试经验、已知问题、失败分析沉淀
api/             API 自动化测试资产
  inventory/     接口文档扫描清单
  p0/            P0 场景、用例、最近一次报告
  results/       本地原始执行结果，已忽略
  runbooks/      API 执行和调试入口文档
ui/              UI 自动化测试
  cases/         Playwright 用例
  elements/      页面对象和操作封装
  framework/     UI 测试基础能力，如环境读取、Network 记录
  data/          UI 测试数据
  reports/       UI 可读报告
  results/       UI 原始执行结果，已忽略
performance/     性能测试
scripts/         辅助脚本
```

## 当前状态

当前阶段：P0 核心自动化已形成可执行基线

- P0 只读 smoke：30 条，客户端 25 条 + 后台 5 条。
- P0 主流程写操作：注册通过、充值订单创建通过、提现申请待继续定位。
- UI 自动化骨架：已接入 Playwright，先用于客户端主流程扫描和真实接口链路捕获。

## UI 自动化

首次使用：

```bash
npm install
npx playwright install
```

配置本地 `.env`：

```bash
CLIENT_BASE_URL=https://client-fat.filbet2025.com
CLIENT_PHONE=<client phone>
CLIENT_OTP=<fat otp>
PLAYWRIGHT_CHANNEL=
```

常用命令：

```bash
npm run test:ui:p0
npm run test:ui:p0:scan
npm run test:ui:p0:pn
npm run test:ui:inventory
npm run test:ui:login
npm run test:ui:game-bet
npm run ui:p0-points
```

- `npm run test:ui:p0`：执行客户端 P0 UI 默认套件，包含登录正反例、主流程扫描、游戏启动冒烟、页面状态正反例；默认不做真实资金动作。
- `npm run test:ui:p0:scan`：只执行 Playwright P0 客户端主流程扫描用例。
- `npm run test:ui:p0:pn`：只执行客户端 P0 UI 正反例补充用例。
- `npm run test:ui:inventory`：按 `ui/data/client-pages.json` 扫描客户端页面定位资产，输出 `ui/reports/client-locator-inventory.md`。
- `npm run test:ui:login`：执行客户端登录正反例。
- `npm run test:ui:game-bet`：登录后进入配置的游戏页；默认只验证启动，设置 `EXECUTE_BET=true` 才点击游戏内投注区域。
- `npm run ui:p0-points`：根据 `ui/data/client-p0-test-points.json` 生成客户端 P0 UI 测试点报告。
- UI 原始 JSON、截图、视频索引在 `ui/results/`，默认不提交 Git。
- `PLAYWRIGHT_CHANNEL` 默认留空，使用 Playwright 自带 Chromium；需要指定本机 Chrome 时再设置为 `chrome`。

## 使用原则

- 先完善规划，再分阶段落地。
- 先做 P0 核心链路，再扩展 P1、P2。
- API P0 资产放在 `api/p0/`；UI 用例、配置、报告分别放在 `ui/cases/`、`ui/data/`、`ui/reports/`。
- 敏感信息不提交到 Git。
- 测试账号、Token、Cookie、环境变量使用本地配置或 CI 凭据管理。
