# P0 API 资产说明

P0 只保留必要资产，避免 CSV 和 Markdown 重复维护。

## 保留文件

| 文件 | 用途 |
| --- | --- |
| `interface-shortlist.csv` | 从全量接口清单筛出的 P0 候选接口池，不直接作为门禁执行 |
| `main-flow-scenarios.csv` | P0 主流程正反例矩阵，决定哪些场景有测试价值 |
| `test-cases.csv` | P0 可执行正例用例，runner 直接读取 |

## 执行规则

- `test-cases.csv` 是当前等级的可执行用例，不是所有等级混在一起的总表。
- 后续 P1、P2 各自使用 `api/p1/test-cases.csv`、`api/p2/test-cases.csv`。
- `main-flow-scenarios.csv` 是业务场景矩阵，用来管理登录注册、KYC 查询前置、充值、投注、派彩结果、提现和后台数据展示；统一执行入口会用它生成 `api/results/p0-main-flow-report.md`。
- `test-cases.csv` 中每条可执行用例都要带 `scenario_id`，这样执行结果能回填到主流程报告。
- `interface-shortlist.csv` 是候选池，用来从接口文档向可执行用例过渡。
- 同名 Markdown 说明不再保留；规则统一写在本文件、`README.md`、`api/runbooks/` 或 `harness/`。
- API 执行报告不是固定资产，统一写入 `api/results/`。UI 结果不得写入 `api/results/`，必须放到 `ui/results/` 或 `ui/reports/`。
- `api/results/` 只保留最近一次执行结果。所有 P0 runner 和报告脚本使用固定文件名覆盖输出，不按日期或次数增量生成报告。

## 推荐命令

执行 P0 API 正反例：

```bash
python3 scripts/run-api-tests.py p0
```

执行 P0 和 P1：

```bash
python3 scripts/run-api-tests.py p0 p1
```

执行 P0 并包含受控写流程：

```bash
python3 scripts/run-api-tests.py p0 --include-write
```

生成结果：

- `api/results/p0-smoke-result.json`
- `api/results/p0-smoke-report.md`
- `api/results/p0-negative-result.json`
- `api/results/p0-negative-report.md`
- `api/results/p0-main-flow-report.md`
- `api/results/main-positive-flow-result.json`，仅 `--include-write` 时生成

这些文件都是可再生成产物，不属于 P0 固定资产；清理旧报告时可以直接删除。

统一入口 `python3 scripts/run-api-tests.py ...` 会在执行前清空 `api/results/`，再写入本次结果。
