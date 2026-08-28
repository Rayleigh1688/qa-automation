# P0 API 资产说明

P0 只保留必要资产，避免 CSV 和 Markdown 重复维护。

## 保留文件

| 文件 | 用途 |
| --- | --- |
| `interface-shortlist.csv` | 从全量接口清单筛出的 P0 候选接口池，不直接作为门禁执行 |
| `main-flow-scenarios.csv` | P0 主流程正反例矩阵，决定哪些场景有测试价值 |
| `test-cases.csv` | P0 可执行接口用例索引；当前安全正例由 smoke runner 读取，反例执行逻辑待迁移为同一 CSV 驱动 |

## 执行规则

- `test-cases.csv` 是当前等级的可执行用例索引，不是所有等级混在一起的总表。当前反例仍由 `api-p0-negative-runner.py` 内的映射驱动，这是待收敛的技术债，禁止再新增第二份反例清单。
- 后续 P1、P2 各自使用 `api/p1/test-cases.csv`、`api/p2/test-cases.csv`。
- `main-flow-scenarios.csv` 是业务场景矩阵，用来管理登录注册、KYC 查询前置、充值、投注、派彩结果、提现和后台数据展示；统一执行入口会用它生成 `api/results/p0-main-flow-report.md`。
- `test-cases.csv` 中每条可执行用例都要带 `scenario_id`，这样执行结果能回填到主流程报告。
- `interface-shortlist.csv` 是候选池，用来从接口文档向可执行用例过渡。
- 同名 Markdown 说明不再保留；规则统一写在本文件、`README.md`、`api/runbooks/` 或 `harness/`。
- API 执行报告不是固定资产，统一写入 `api/results/`。UI 结果不得写入 `api/results/`，必须放到 `ui/results/` 或 `ui/reports/`。
- `api/results/` 只保留最近一次执行结果。所有 P0 runner 和报告脚本使用固定文件名覆盖输出，不按日期或次数增量生成报告。

## 推荐命令

执行完整当前 P0 主流程（默认包含受控读写）：

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

需要显式指定专用提现账号时：

```bash
python3 scripts/run-api-tests.py p0 \
  --write-client-phone <controlled write/deposit phone> \
  --write-client-otp <otp code> \
  --withdraw-client-phone <withdraw dedicated phone> \
  --withdraw-client-otp <otp code>
```

生成结果：

- `api/results/p0-smoke-result.json`
- `api/results/p0-smoke-report.md`
- `api/results/p0-negative-result.json`
- `api/results/p0-negative-report.md`
- `api/results/p0-main-flow-report.md`
- `api/results/p0-api-report.html`，静态可视化主流程报告
- `api/results/main-positive-flow-result.json`，完整 P0 默认生成；`--safe-only` 时不生成

这些文件都是可再生成产物，不属于 P0 固定资产；清理旧报告时可以直接删除。

统一入口 `python3 scripts/run-api-tests.py ...` 会在执行前清空 `api/results/`，再写入本次结果。

## 接口版本监控

接口文档中的旧路径不能因为 HTTP `200` 就继续作为正例。以当前前端可用路径为正例门禁，旧路径保留为替代关系或反例保护；每次版本发布均通过 P0 报告和 `harness/known-errors.md` 同步结论。

| 旧接口或旧行为 | 当前使用路径 | P0 处理 |
| --- | --- | --- |
| `/member/game/list` | `/member/v2/index`、`/member/game/listRw`、`/member/game/list/recommend` | 新路径做正例；旧路径 `status=false` 不得判通过 |
| `/member/vip` | `/promo/vip/config`、`/promo/vip/sign/in/config` | 新路径做正例；旧路径业务失败由反例 runner 保护 |
| 接口文档标为 GET 的后台财务待审列表 | 实际 POST + CBOR 请求体 | 以实测 POST 方式执行，GET 405 记录为接口资产差异 |
| 充值通道 `min_amount/max_amount` | `/finance/payment/deposit` 服务端实际校验 | 当前 FAT 未执行限额校验；显式运行 `--include-deposit-limit-contract` 复验，修复前不进入默认 CI |

## 主流程下一步计划

当前 P0 API 主流程下一步不扩散到 P1/P2，先把正例主流程跑通并稳定：

1. 客户端登录和新增测试用户注册。
2. KYC 查询和 eKYC 配置查询。
3. 充值渠道、充值下单、后台补单和充值记录查询。
4. 游戏列表、投注记录、钱包和账变查询；真实投注与派彩 UI 链路转入下一周期探索。
5. 受控写流程使用独立充值账号承接充值/补单，使用无流水限制、已 KYC、已绑定提款账户的专用账号创建提现单；随后在 FAT/UAT 后台审核并标记成功。无需校验项目外收款账户或真实到账。
6. 后台只读展示优先校验登录用户、银行卡、账变类型、KYC 待审数量、eKYC 配置，以及受控写流程生成的充值/提现待审列表。
7. FAT/UAT 的 `--main-positive-flow` 会对本次专用测试提现单执行审核同意和标记成功；不调用或验证第三方出款。KYC 成功状态可通过后台直接准备，KYC 资料提交链路仍作为独立测试。

## 测试数据分层

- `CLIENT_PHONE`：只读 smoke 账号，必须可登录，且最好是已 KYC、已绑定提款账户的成熟账号；否则提款账户列表等只读断言会失败。
- `WRITE_CLIENT_PHONE`：受控写/充值账号，可以是普通可登录账号，用于充值下单和后台补单；该账号会因补单产生流水，不要拿来做提现正例。
- `WITHDRAW_CLIENT_PHONE`：提现专用账号，必须已 KYC、已绑定提款账户、无未完成流水、可提现余额大于本次提现金额。FAT/UAT 可通过后台受控补资或维护账号池；不需要项目外收款账户。
- 充值和提现账号必须拆开；如果复用，充值补单产生的流水锁定会让提现正例变成业务失败。
