# AI 对话交接

这是新 AI 或新对话进入仓库的第一份文档。它只保存当前状态、最新证据、已接受例外和下一步；长期方法、执行手册与排障记录由下层文档维护。

## 一分钟结论

- P0 基线已完成一次修正版完整统一入口验证；当前进入提交冻结和服务器/CI 数据配置，不扩展活动、VIP、代理、OCR/eKYC 等 P1/P2 矩阵。
- API 固定资产为 8 条主流程、57 条整体用例：31 条 safe smoke、15 条 API 登记反例、10 条受控写/UI 协作项和 1 条已封装的新号状态 UI 反例。
- 2026-08-31 FAT safe smoke 31/31、默认安全反例 13/13 已通过。
- P0 快速门禁已连续执行 3 轮：每轮 API safe smoke 31/31、默认反例 13/13；默认 UI 前两轮 10/11（仅已确认的未勾选条款产品缺陷），第三轮 11/11，没有出现环境外随机失败。
- 主账号采用单次密码登录，UI storage state 与 API session 双向同步 token；只读校验已证明复用时不会再次请求 client/admin 登录接口。
- 当前本地配置的只读、资金流和已 KYC 别名仍指向同一个已验证账号；账号状态清单已统一到 `api/p0/test-account-pool.csv`。`PRE_KYC_CLIENT_PHONE` 永久保留为未 KYC 反例账号，不得提交 KYC；KYC 闭环使用独立账号。最低提现金额走成熟账号 API 小金额反例，不准备低余额账号。本地配置已收敛为 `.env`。
- KYC 最小闭环已完成：后台按本次 uid 定位并审批成功，客户端刷新为 `kyc_status=5`；已通过池账号后续只复核状态，不重复提交。
- 2026-08-31 修正版 `npm run test:p0:full` 已完整通过：永久未 KYC 拦截 1/1、safe 31/31、默认反例 13/13、默认 UI 11/11；充值 1200 后产生 1800 流水，以固定单注 1000 完成 2 次真实投注并归零，API 提现 1000 成功进入后台 `under_review`。
- `p0-reconciliation-result.json` 已 PASS：充值创建/补单 ID、钱包 +1200、流水归零、提现前后台 ID/uid/金额均一致。
- 最新本地主流程报告为 8/8；API 提现建单已恢复为完整资金链的独立步骤。Maya UI 提现与 DTC-002 新号 KYC 前提现拦截分别作为独立 UI P0，其中 DTC-002 已用新号实际通过且零提现请求。

## 阅读链：由浅入深

1. 本文件：确认当前结论、例外和下一步。
2. [`README.md`](README.md)：全局目录、统一命令、CI、敏感信息和结果边界。
3. [`.agents/skills/filbet-p0-automation/SKILL.md`](.agents/skills/filbet-p0-automation/SKILL.md)：Codex 自动发现的任务路由。
4. [`skills/README.md`](skills/README.md)：选择 API、UI 或业务规则方法。
5. 子项目：[`api/p0/README.md`](api/p0/README.md)、[`ui/README.md`](ui/README.md)、`api/runbooks/`。
6. 发生失败时才进入 [`harness/README.md`](harness/README.md)。
7. 最后查看 `api/results/`、`ui/results/`、`ui/reports/` 的最近一次证据；生成物不是规则来源。

开始修改前执行 `git status --short`。工作区存在未提交修改，默认属于用户或当前任务，不得回退无关内容。

## P0 当前覆盖判断

| 流程 | 已有证据 | 仍需补充 | 当前判断 |
| --- | --- | --- | --- |
| 注册登录 | API 注册/登录、登录反例；UI 登录正反例已有实现 | 使用稳定账号全量复跑默认 UI 套件 | 基线已具备 |
| KYC | 新号提交、后台按 uid 审批、前台刷新为 `kyc_status=5` | 扩展驳回重提、OCR/eKYC 等转 P1 | 最小闭环已通 |
| 充值 | 非活动订单、后台补单、相同订单 ID、钱包 +1200 | 上下限缺陷探针等待产品修复 | 主链通过 |
| 投注 | 固定单注 1000，按剩余流水分批投注并轮询归零 | 更深的单局派彩字段矩阵可转 P1 | 主链通过 |
| 投注/派彩记录 | 本轮真实投注、点击次数和异步流水结果已关联 | 复杂输赢/派彩组合可转 P1 | 主链通过 |
| 钱包/账变 | 充值钱包增量、流水归零、提现 uid/金额统一核对 PASS | 扩展账变类型矩阵可转 P1 | 主链通过 |
| 提现 | API 建单与后台精确订单关联；Maya UI 1000 建单独立封装；DTC-002 永久未 KYC 账号拦截已通过 | FAT 真实出款恢复后增强最终状态复验 | P0 通过 |
| 后台权限/报表 | 后台 safe smoke 13/13，本轮订单关联核对 PASS | 真实出款恢复后增强复验 | 主链通过 |

## API 与 UI 资产现状

### API

- `api/p0/test-cases.csv` 是唯一完整用例索引。
- `api/p0/main-flow-scenarios.csv` 只有 8 行，只表示业务顺序和完成标准。
- `api/p0/interface-shortlist.csv` 是接口发现池，不能决定 P0 数量和执行顺序。
- 默认 safe/negative 已覆盖当前用户/权限、KYC 待审查询、充值/提现列表、财务报表、资金记录等结构契约。
- `reconcile-p0-flow.py` 已统一保存并核对 uid、deposit id、钱包增量、投注批次、流水结果和 withdraw id。

### UI

- `npm run test:ui:p0` 当前静态收集 11 条默认测试，覆盖登录、主流程页面扫描、充值页安全契约、游戏启动和页面状态正反例；默认不真实充值、投注或提现。
- 默认套件固定 1 worker，并保留忽略的 storage state；API 固定保留忽略的 session 文件。同一账号的其他进程不得再次登录。
- UI P0 测试点共有 19 条；提现包含 Maya 合法建单正例和永久未 KYC 账号安全前置反例。充值缺少金额/渠道的前端矩阵移出 P0，由 API 业务边界和充值页正向契约覆盖。
- `client-deposit-contract.spec.mjs` 已纳入默认 P0 命令；默认只验证页面、支付方式和金额控件，只有显式 `EXECUTE_DEPOSIT_CONTRACT=true` 才创建充值请求。
- 独立提现 UI 链路已验证：脚本明确选择 Maya，非法金额不会发出提现请求；合法金额 1000 完成钱包密码数字键盘提交，客户端显示成功详情，后台在同一提交时间定位到金额一致的新 `under_review` 订单。GCash 当前返回 `Payment channel unavailable`，不再用于 FAT 提现正例。
- 真实投注由项目 Playwright 自行启动 Chromium，不依赖 Codex 内置浏览器是否存在已连接实例。
- 默认 UI 已连续串行 3 轮：前两轮 10/11（仅已确认条款缺陷），第三轮 11/11；真实投注专项通过并完成流水归零。

## 当前下一步（按价值排序）

1. 冻结并提交当前 P0 基线；生成物继续保留在本地忽略目录，不进入 Git。
2. 将 `test-account-pool.csv` 的各账号 lane 和全部 secret 配置到服务器/CI，首次先执行 quick，再人工触发 full。
3. FAT 转账接口恢复后，新建一笔提现复验后台同意/成功；不得重试已进入待审或已经取消的旧订单。

## 不可违反的边界

- API、UI 和数据库分别提供契约、真实交互、诊断证据，不能互相冒充完整闭环。
- 数据库只读，不直接改 KYC、余额、流水、充值或提现状态。
- 受控写只处理当前 flow 创建的记录；任一业务步骤 `status=false` 时停止，不调用后续 success 接口制造通过。
- 密码、OTP、TOTP seed、token、cookie、设备 ID 和未脱敏个人资料只放忽略的本地配置或 CI 凭据。
- API 结果写 `api/results/`；UI 原始结果写 `ui/results/`；UI 可读报告写 `ui/reports/`。同名覆盖，历史交给 CI。
- 规则更新只改最窄的权威文档，再由上层链接进入；不要复制实时状态到 Skills、Harness 或多个 README。

## 对话结束检查

1. 同步当前证据和下一步到本文件。
2. 将长期规则、执行方法或已知错误分别写回 Skills、runbook 或 Harness。
3. 若用例范围/顺序变化，同步 `api/p0/` 固定资产；若只改变环境接受标准，不改目标场景定义。
4. 说明执行了什么、未执行什么，以及阻塞属于产品、环境、数据还是测试代码。
5. 检查没有提交密钥或带敏感信息的生成报告。
