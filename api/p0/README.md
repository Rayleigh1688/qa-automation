# P0 API 资产说明

P0 只保留必要资产，避免 CSV 和 Markdown 重复维护。

## 保留文件

| 文件 | 用途 |
| --- | --- |
| `interface-shortlist.csv` | 从全量接口清单筛出的 P0 候选接口池，不直接作为门禁执行 |
| `main-flow-scenarios.csv` | 8 条端到端 P0 主流程，只描述业务顺序、账号策略和完成标准 |
| `test-cases.csv` | 完整 P0 用例索引，包含正例、反例、受控写、UI 协作项和测试数据阻塞项 |
| `test-account-pool.csv` | P0 测试账号池规则，记录新账号、只读账号、充值写账号和提现专用账号的用途边界 |

需要追溯接口文档扫描来源时，再进入 [`api/inventory/interfaces.md`](../inventory/interfaces.md)；扫描资产只用于发现，不用于决定 P0 顺序。
按客户端、后台和后台业务模块检索接口时，使用自动生成的 [`api/catalog/`](../catalog/README.md)。FAT/UAT 差异统一维护在 [`api/runbooks/ENVIRONMENTS.md`](../runbooks/ENVIRONMENTS.md)。

## 执行规则

- `test-cases.csv` 是 P0 唯一的完整用例索引。反例 runner 从该 CSV 读取 `negative_smoke` 元数据，不再维护第二份反例清单。
- 后续 P1、P2 各自使用 `api/p1/test-cases.csv`、`api/p2/test-cases.csv`。
- `main-flow-scenarios.csv` 只有 8 行，顺序固定为注册登录、KYC、充值、投注、投注/派彩记录、钱包与账变、提现、后台总核对。它不是接口级用例表，所以数量必须小于 `test-cases.csv`。
- `test-cases.csv` 按 `case_order` 物理排序，每条用例通过 `scenario_id` 归属一条主流程，并通过 `polarity`、`execution_policy`、`account_lane` 明确正反例、执行方式和账号用途。
- `interface-shortlist.csv` 只负责接口发现。进入 P0 和执行顺序由真实客户端 Network、业务依赖和 `build-p0-test-cases.py` 的显式核心路径决定，不能按接口文档顺序直接生成。
- 有状态动作必须严格按主流程执行，并沿用本次产生的 uid、订单号或投注标识；否则后续列表即使返回成功，也不能证明是本次动作的结果。纯只读 safe smoke 使用一个成熟账号验证接口契约，仍按主流程排序以方便定位，但不把这种结构检查冒充端到端闭环。
- `account_lane` 是执行约束：safe smoke 客户端查询使用 `mature_read_account`；资金正向链路从充值到提现统一使用 `fund_flow_account`；未 KYC 反例固定使用永久 BASIC 账号，KYC 闭环使用另一账号，活动流水专项不进入 P0 lane。
- 每个账号 lane 只成功登录一次。`api/results/p0-api-session.json` 在 safe、negative、controlled 阶段之间传递 client/admin token；runner 先以只读详情接口验证 token，失效时才允许重新登录。禁止负例 runner 为获取前置数据再次成功登录。
- 同名 Markdown 说明不再保留；规则统一写在本文件、`README.md`、`api/runbooks/` 或 `harness/`。
- API 执行报告不是固定资产，统一写入 `api/results/`。UI 结果不得写入 `api/results/`，必须放到 `ui/results/` 或 `ui/reports/`。
- `api/results/` 只保留最近一次执行结果。所有 P0 runner 和报告脚本使用固定文件名覆盖输出，不按日期或次数增量生成报告。

## 跨 API、UI 与数据库的资金链放行规则

正式业务顺序以 `main-flow-scenarios.csv` 的 8 条主流程为准。资金链在不同执行面之间切换时还必须满足以下规则：

1. 充值、投注、流水核对和提现统一使用同一个 `fund_flow_account`，整条资金链串行执行。
2. 账号在会话准备阶段只成功登录一次。API 复用忽略的 `api/results/p0-api-session.json`，UI 复用忽略的 `ui/results/client-p0-storage-state.json`；切换执行面时同步 token，不另起进程重复登录同一账号。
3. API 完成充值、后台补单和钱包核对后必须停止。普通存款即使不参加活动也会产生基础流水，不能直接跳到提现。
4. UI 三方游戏单注读取 `CLIENT_GAME_BET_AMOUNT`：FAT/UAT 当前统一为 100。`scripts/run-turnover-bet.py` 只读汇总全部未完成流水，按当前环境单注计算投注次数并设置安全上限；FAT 默认读取只读数据库，UAT 默认通过管理后台会员列表和流水列表读取，不要求数据库连接。
5. 投注后轮询 Bet History、钱包、账变和基础流水；以本轮时间窗口和关联标识核对记录。只有总剩余流水为 0，才允许发起提现。
6. 提现金额必须同时满足余额和通道限制。完整 API 资金链通过 `/finance/payment/withdraw` 创建订单，再由后台 API 按订单 ID 精确定位并核对；Maya UI 建单另作独立 UI P0，不替代 API CTC-009。
7. 数据库只用于只读诊断和交叉核对，不直接修改 KYC、余额、流水、充值或提现状态。

## 推荐命令

执行可重复快速 P0 门禁（不新增资金写入）：

```bash
npm run test:p0
```

执行完整受控 P0 验收：

```bash
npm run test:p0:full
```

只执行 API 到充值与补单检查点：

```bash
python3 scripts/run-api-tests.py p0
```

执行 P0 和 P1：

```bash
python3 scripts/run-api-tests.py p0 p1
```

只执行只读/反例快速检查：

```bash
python3 scripts/run-api-tests.py p0 --safe-only
```

需要显式指定资金主流程账号时：

```bash
python3 scripts/run-api-tests.py p0 \
  --register-phone <allocated 090XXXXXXXX KYC phone> \
  --write-client-phone <fund flow phone> \
  --write-client-otp <otp code> \
  --deposit-amount 1200
```

生成结果：

- `api/results/p0-smoke-result.json`
- `api/results/p0-smoke-report.md`
- `api/results/p0-negative-result.json`
- `api/results/p0-negative-report.md`
- `api/results/p0-main-flow-report.md`
- `api/results/p0-api-report.html`，静态可视化主流程报告
- `api/results/fund-flow-seed-result.json`，默认只生成充值与补单阶段证据；`--safe-only` 时不生成
- `api/results/kyc-result.json`，KYC 提交/已存在状态、后台审批与前台刷新证据
- `api/results/p0-reconciliation-result.json`，本轮充值、钱包、投注流水、提现及后台订单关联断言

这些文件都是可再生成产物，不属于 P0 固定资产；清理旧报告时可以直接删除。

统一入口 `python3 scripts/run-api-tests.py ...` 会在执行前清空普通结果，再写入本次结果；被 Git 忽略的 `p0-api-session.json` 会保留，避免清理动作迫使账号重新登录。

## 接口版本监控

接口文档中的旧路径不能因为 HTTP `200` 就继续作为正例。以当前前端可用路径为正例门禁，旧路径保留为替代关系或反例保护；每次版本发布均通过 P0 报告和 `harness/known-errors.md` 同步结论。

| 旧接口或旧行为 | 当前使用路径 | P0 处理 |
| --- | --- | --- |
| `/member/game/list` | `/member/v2/index`、`/member/game/listRw`、`/member/game/list/recommend` | P0 正例以客户端真实新版路径为准；旧路径 2026-08-31 FAT 又返回 `status=true`，仅作兼容观察，不断言必须失败 |
| `/member/vip` | `/promo/vip/config`、`/promo/vip/sign/in/config` | VIP 不属于当前 P0 主流程；新旧路径都留在候选池，不进入 P0 门禁 |
| 接口文档标为 GET 的后台财务待审列表 | 实际 POST + CBOR 请求体 | 以实测 POST 方式执行，GET 405 记录为接口资产差异 |
| 充值通道 `min_amount/max_amount` | `/finance/payment/deposit` 服务端实际校验 | 当前 FAT 未执行限额校验；显式运行 `--include-deposit-limit-contract` 复验，修复前不进入默认 CI |
| 旧充值渠道参数 `mode=2&source=huawei` | `/finance/channel/list?mode=1` | 按客户端充值页真实请求做正例门禁 |
| 充值记录旧 `status=PENDING` 筛选 | `/finance/deposit/list?page=1&page_size=10&time_flag=0` | 按 Transaction/Deposit 记录页真实请求做正例门禁 |
| 投注记录旧 `time_flag=30&status=1` 筛选 | `/member/game/bet/list?page_size=10&time_flag=0&page=1` | 按 Bet History 真实请求做正例门禁 |

## 主流程下一步计划

当前资产为 8 条主流程、57 条整体 P0 用例：31 条 safe smoke（客户端 18、后台 13）、15 条 API 登记反例（默认执行 13 条，充值上下限 2 条为显式缺陷探针）、10 条受控写/UI 协作项，以及 1 条已实现的状态 UI 反例。更换成熟账号后 FAT safe smoke 已通过 31/31，默认安全反例通过 13/13。

1. 永久 BASIC 账号只验证 KYC/钱包密码双前置，不提交 KYC；KYC 最小闭环使用独立的新号或可重提账号。
2. 已通过 KYC 的账号只复核状态，不执行重复提交；注册、KYC、资金链账号必须遵循 `test-account-pool.csv` 的 lane 边界。
3. 充值、投注和提现复用同一个 `fund_flow_account`；主链路只做不参加活动的充值。普通存款基础流水在提现前完成，但不专门发起流水限制反例。
4. 投注之后先核对投注/派彩记录，再核对钱包与前后台账变，最后进入提现。
5. 活动配置、活动流水限制、盲盒、Filcoin、VIP、代理、收藏等均移出 P0 门禁；活动流水限制作为 P1 独立专项，不参与 P0 放行。
6. 后台查询穿插在对应业务阶段：KYC 后查待审，充值后查待审/补单，提现后查审核；当前用户权限与汇总报表放在最后总核对。

后台列表类 POST 接口必须以 CBOR 发送请求体；充值/提现待审与财务报表使用最近两天的秒级动态时间窗口。`test-cases.csv` 的 `request_body` 支持 `{{now_minus_2d}}`、`{{now_plus_5m}}`，runner 会在执行时替换为整数时间戳。接口文档中把部分待审列表标为 GET 的记录已经实测纠正为 POST。

当前核对深度：客户端账变与后台账变的结构查询已分别进入 safe smoke；本轮充值和提现已完成订单号、uid、金额与待审状态的一对一关联。真实出款成功/取消后的最终状态和账变方向复验属于 FAT 转账接口恢复后的增强项，不阻塞当前 P0。

当前 FAT 阶段接受标准：Maya 提现单成功创建、进入后台待审列表、取消/退款后前后台金额和最终状态一致，即可视为提现提交链路通过。`No available transfer interface` 之后的真实出款成功属于环境恢复后的增强复验；目标场景仍保留后台成功闭环，不因环境例外删除。

KYC 保留最小 P0 闭环：真实提交、后台审核以及审核后前台状态刷新。页面 `KYC successful` 只代表资料已提交等待处理，不等于审核通过。驳回重提、OCR/eKYC、证件类型和字段组合等扩展矩阵归 P1。

## 测试数据分层

完整账号状态、是否必须预备、复用规则和环境变量映射以 [`test-account-pool.csv`](test-account-pool.csv) 为准。准备账号时记录 phone、uid、已知密码、KYC 状态、提款账户状态、未完成流水、可提现余额和最后验证时间，但实际值只写本地忽略的 `.env*`，不要写入 CSV。

- `CLIENT_PHONE`：只读 smoke 账号，必须可使用 `CLIENT_PASSWORD` 登录，且最好是已 KYC、已绑定提款账户的成熟账号；否则提款账户列表等只读断言会失败。
- `WRITE_CLIENT_PHONE`：`fund_flow_account`，必须是普通可登录、已 KYC、已绑定提款账户的会员；从充值补单开始，复用到投注、流水和提现。
- `BET_CLIENT_PHONE`、`WITHDRAW_CLIENT_PHONE`：兼容别名，可以指向同一个 `fund_flow_account`。
- `RESTRICTED_CLIENT_PHONE`：P1 活动流水专项预留变量，不参与 P0 主流程放行判断。
- 维护一个永久 BASIC/未 KYC 账号专用于 DTC-002，绝不提交 KYC；KYC 闭环使用独立账号。最低提现金额使用已绑定提款账户的成熟账号直接走 API 小金额反例，不维护低余额账号。
- KYC 探索使用 `090XXXXXXXX` 新账号池，首个账号从 `09000000001` 开始；测试环境 OTP 固定为 `111111`。已驳回或未通过 KYC 的账号可以重复提交 KYC，避免账号池被快速用尽。
- `9888888050` 已知存在提现流水限制，不作为默认提现正例账号；除非先在后台解除流水限制，否则提现失败属于测试数据前置问题。
- 充值页面的 `Multiple Deposit Bonus` 活动开关默认不参加；参加充值活动会产生提现流水限制。需要做无流水限制提现链路时，应保持该开关关闭/置灰。
