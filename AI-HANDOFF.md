# AI 对话交接

这是新 AI 或新对话进入仓库的第一份文档。它只保存当前状态、最新证据、已接受例外和下一步；长期方法、执行手册与排障记录由下层文档维护。

## 一分钟结论

- P0 基线提交为 `90b24e3`。当前只做 P0，不扩展 P1/P2，也不处理 Jenkins。
- 固定资产为 8 条主流程、57 条整体用例：31 条 safe smoke、15 条 API 登记反例、10 条受控写/UI 协作项和 1 条新号状态 UI 反例。`api/p0/test-cases.csv` 是唯一完整用例索引。
- 2026-09-02 FAT 全量已通过：safe API 31/31、默认反例 13/13、默认 UI 11/11、永久 BASIC 提现拦截 1/1，充值、真实投注、流水归零、提现和统一核对均 PASS。
- 2026-09-02 UAT 主流程报告 8/8、统一资金链核对 10/10 PASS：Maya 充值 1200；BNG `Coins` 单注 100 完成 6/6 次真实投注；剩余流水 535→0；投注后可提现余额 804，按合法档位提现 500 并与后台同订单 `under_review` 精确匹配；投注后客户端 safe API 18/18、后台 safe API 13/13。
- UAT 默认 UI 为 10/11，唯一失败是“未勾选登录条款仍可登录”。用户明确接受本轮临时例外，但缺陷本身未关闭，后续不能写成 UI 全通过。
- FAT 既有账号使用密码登录；UAT 使用客户端真实发短信、按响应中的同一 ID 经 `/admin/sms/auth` 取动态验证码，再提交 `/member/otp/login/v2`。UAT 禁止固定 `111111`。Playwright 会在解析配置前加载环境文件，并校验客户端 origin，防止 FAT/UAT 混用。
- FAT/UAT 业务单注统一为 100。厂商请求里的缩放金额只作观察，真实金额由投注记录、钱包、账变和流水交叉证明。游戏厂商/身份检查必须在选择金额和 Spin 前完成，失败时不寻找替代游戏。
- UAT 无数据库访问，流水通过后台会员与流水接口只读核对；数据库在其他环境也仅可只读诊断。
- 永久 BASIC 账号与 KYC 闭环账号严格分离；BASIC 账号不得提交 KYC、设置钱包密码或充值。新号默认从 `9000000001` 起通过后台会员列表逐号查找。
- 2026-09-04 API 执行模型已改为每个 runner 启动时强制 fresh login，token 只在本次进程内共享，不再跨命令保存或复用 session。FAT `npm run test:p0:api` 最新联网结果为 `PASS/complete`、90/90：safe 31/31、默认反例 13/13，以及新号注册、KYC 提交/后台审批、充值创建/同单补单/钱包到账、流水发现与清空、钱包密码、Maya 账户绑定、提现创建和前后台同订单精确核对均通过；纯 API 命令不执行三方真实投注。`amount_limit` 是快捷金额列表，硬校验使用 `min_amount/max_amount`；同额快捷档位仅作为自动选通道的优先项。API 入口将前置检查、子进程和未知异常统一转成非零退出与稳定 `FAILED/BLOCKED` 报告，报告渲染失败时写最小兜底报告。
- 2026-09-04 报告拆为同模板、不同统计对象的三份 HTML：API 请求/断言报告 `api/results/p0-api-report.html`，Playwright 用例报告 `ui/reports/p0-ui-report.html`，完整组合验收的 8 条主流程报告 `api/results/p0-main-flow-report.html`。API 单命令不再因未执行 UI 证据显示 `PARTIAL`；报告时间固定显示 UTC+8，API 报告从 run status 展示整秒级总执行耗时。
- 环境差异以 `api/runbooks/ENVIRONMENTS.md` 为准，执行方法看 API/UI runbook，已知故障看 Harness；结果目录只保存最近一次证据。

## 阅读链：由浅入深

1. 本文件：确认当前结论、例外和下一步。
2. [`README.md`](README.md)：全局目录、统一命令、CI、敏感信息和结果边界。
3. [`.agents/skills/filbet-p0-automation/SKILL.md`](.agents/skills/filbet-p0-automation/SKILL.md)：Codex 自动发现的任务路由。
4. [`skills/README.md`](skills/README.md)：选择 API、UI 或业务规则方法。
5. 子项目：[`api/p0/README.md`](api/p0/README.md)、[`ui/README.md`](ui/README.md)、`api/runbooks/`；环境差异看 [`ENVIRONMENTS.md`](api/runbooks/ENVIRONMENTS.md)，接口分类看 [`api/catalog/`](api/catalog/README.md)。
6. 发生失败时才进入 [`harness/README.md`](harness/README.md)。
7. 最后查看 `api/results/`、`ui/results/`、`ui/reports/` 的最近一次证据；生成物不是规则来源。

开始修改前执行 `git status --short`。工作区存在未提交修改，默认属于用户或当前任务，不得回退无关内容。

## P0 当前覆盖判断

| 流程 | 已有证据 | 仍需补充 | 当前判断 |
| --- | --- | --- | --- |
| 注册登录 | FAT/UAT API 与 UI 登录均已执行；UAT 动态短信 OTP 已通过 | 修复未勾选条款仍可登录 | 主链通过，保留 1 个产品缺陷 |
| KYC | 新号提交、后台按 uid 审批、前台刷新为 `kyc_status=5` | 扩展驳回重提、OCR/eKYC 等转 P1 | 最小闭环已通 |
| 充值 | FAT/UAT 均完成非活动订单、后台补单、相同订单 ID、钱包 +1200；UAT 使用 Maya | GCash、QRPH/PESONET 在 UAT 当前不可用 | 主链通过 |
| 投注 | FAT Lucky Penny 与 UAT BNG `Coins` 均有真实单注 100 证据；UAT 6/6 次 | 扩展游戏矩阵转 P1 | 主链通过 |
| 投注/派彩记录 | 本轮真实投注、点击次数和异步流水结果已关联 | 复杂输赢/派彩组合可转 P1 | 主链通过 |
| 钱包/账变 | 充值钱包增量、流水归零、提现 uid/金额统一核对 PASS | 扩展账变类型矩阵可转 P1 | 主链通过 |
| 提现 | API 建单与后台精确订单关联；UAT 本轮 Maya 500 进入 `under_review`；DTC-002 已通过 | 真实出款完成态属于环境恢复后的增强复验 | P0 通过 |
| 后台权限/报表 | 后台 safe smoke 13/13，本轮订单关联核对 PASS | 真实出款恢复后增强复验 | 主链通过 |

## API 与 UI 资产现状

### API

- `api/p0/test-cases.csv` 是唯一完整用例索引。
- `api/p0/main-flow-scenarios.csv` 只有 8 行，只表示业务顺序和完成标准。
- `api/p0/interface-shortlist.csv` 是接口发现池，不能决定 P0 数量和执行顺序。
- `api/catalog/` 是从全量 inventory 自动生成的调用端/业务模块检索视图，不是新的用例源。
- 默认 safe/negative 已覆盖当前用户/权限、KYC 待审查询、充值/提现列表、财务报表、资金记录等结构契约。
- `reconcile-p0-flow.py` 已统一保存并核对 uid、deposit id、钱包增量、投注批次、流水结果和 withdraw id。

### UI

- `npm run test:ui:p0` 当前静态收集 11 条默认测试，覆盖登录、主流程页面扫描、充值页安全契约、游戏启动和页面状态正反例；默认不真实充值、投注或提现。
- 每个 API runner 和每次 UI 命令都从 fresh login 开始；token/storage state 只允许在同一次进程或 Playwright suite 内共享，生成物清理时不再保留到下一次运行。默认 UI suite 仍固定 1 worker。
- UI P0 测试点共有 19 条；提现包含 Maya 合法建单正例和永久未 KYC 账号安全前置反例。充值缺少金额/渠道的前端矩阵移出 P0，由 API 业务边界和充值页正向契约覆盖。
- `client-deposit-contract.spec.mjs` 已纳入默认 P0 命令；默认只验证页面、支付方式和金额控件，只有显式 `EXECUTE_DEPOSIT_CONTRACT=true` 才创建充值请求。
- 独立提现 UI 链路已验证：脚本明确选择 Maya，非法金额不会发出提现请求；合法金额 1000 完成钱包密码数字键盘提交，客户端显示成功详情，后台在同一提交时间定位到金额一致的新 `under_review` 订单。GCash 当前返回 `Payment channel unavailable`，不再用于 FAT 提现正例。
- 真实投注由项目 Playwright 自行启动 Chromium，不依赖 Codex 内置浏览器是否存在已连接实例。
- 最新 UAT 默认 UI 为 10/11，唯一失败为已接受但未修复的条款缺陷；真实投注专项和流水归零均已通过。

## 当前下一步（按价值排序）

1. 2026-09-04 起暂停继续扫描接口，第一优先级转为让 P0 完全脱离 AI 临场操作和判断。FAT API 单命令已经联网验收通过；下一检查点是单独执行 `ENV_FILE=.env.fat npm run test:ui:p0`，确认 Playwright 从 fresh login 开始、无需 AI 操作、成功或失败均稳定生成 UI HTML 报告。UI 独立通过后再执行 `ENV_FILE=.env.fat npm run test:p0:full` 验证 API + UI 总编排。现有 P0/P1 范围不变。
2. FAT 接口发现的会员列表和详情内部操作补扫已完成：会员列表形成 30 个动作结论，Batch/全部筛选族/组合查询/分页/行内入口已有证据，`POST /admin/member/list` 对比文档 GET 定义归类 `MISCLASSIFIED`；17/17 详情页签完成 DOM 清单，14 个数据页签形成 72 个 UI 动作结论、76 条 action-endpoint 映射。Export 以触发接口为完成标准，不保存文件；Deposit Export 实际触发但空数据业务失败，其余未捕获 Network 的点击不虚报接口。KYC 保持 `0→2→3→2→5`；Bet/Login、Risk Control、Wallet `0→0.01→0`、VIP `V0→V1→V0`、充值倍率和 Turnover `0→1→0` 均完成可恢复闭环并恢复。流水 add/sub 均 HTTP 200、业务成功，数据库只读确认同一行 finished 且 locked=0；clear 和 Token 调整未请求。独立写操作资产为 32 行、18 个唯一已触发接口：`ACTIVE 21`、`ACTIVE_FAILED 1`、`DOCUMENTED_UNVERIFIED 6`、`UNDOCUMENTED_ACTIVE 1`、`MISCLASSIFIED 3`，无意外未恢复副作用。独立管理后台合并结果为 135 个唯一 method+path，连同客户端 59 个共 194 个首方接口；共享 inventory/catalog 尚未修改。184 个安全跳过、6 个交互错误和 60 个旧写阻塞项已生成逐行审计，未仅凭未扫描到判 `STALE`。合规管理后台、代理管理后台和代理前台已分别用互相隔离的 Playwright context 完成当前账号权限面扫描：合规仅渲染 `/#/reportCenter/pagcor`，动态 5 个接口均 `ACTIVE`，权限树 63/63 成功；代理管理使用新二维码实时 TOTP 登录后渲染 11 个菜单，11/11 页面通过鉴权/路由硬门禁，动态 18 个接口为 `ACTIVE 16`、`UNDOCUMENTED_ACTIVE 1`、`MISCLASSIFIED 1`；代理前台 Code Login 后动态验证 5/5 路由，11 个唯一接口均 `ACTIVE`。三个调用端均无合法本轮持久写目标，写请求为 0；未观察文档接口保持 `DOCUMENTED_UNVERIFIED`。当前冻结为阶段快照；只有用户明确恢复专项时才继续补扫、分类或等级评审。
3. 不重放本轮 UAT 充值、投注或提现订单；下一次完整资金链必须创建并关联新的 flow。
4. 未勾选登录条款缺陷修复后，只重跑默认 UI 11 项并取消临时接受例外。

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
