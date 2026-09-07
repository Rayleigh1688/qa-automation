# FAT 当前接口数量对比

口径：2026-09-03 当前已提交的 FAT UI Network 证据，按 `method + 标准化 path` 去重。主管理后台使用会员缺口阶段的独立合并结果；客户端在首轮 53 个首方接口上合并 KYC 状态链新增接口。第三方接口不计入首方总数。

| 调用端 | 动态首方接口 | ACTIVE | ACTIVE_FAILED | UNDOCUMENTED_ACTIVE | MISCLASSIFIED | 第三方 | 可用文档接口 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 客户端 | 59 | 47 | 1 | 0 | 11 | 7 | 169 |
| 主管理后台 | 135 | 113 | 1 | 18 | 3 | 0 | 561 |
| 合计 | 194 | 160 | 2 | 18 | 14 | 7 | 730 |

## 与接口文档精确对账

| 调用端 | method+path 精确匹配 | 动态但无同调用端精确文档 | 文档存在但当前 UI 未观察 | 动态数/文档数 | 精确文档覆盖率 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 客户端 | 47 | 12 | 122 | 34.9% | 27.8% |
| 主管理后台 | 113 | 22 | 448 | 24.1% | 20.1% |
| 合计 | 160 | 34 | 570 | 26.6% | 21.9% |

“动态但无精确文档”包含未登记接口、GET/POST method drift 和调用端/业务分类错误，不能全部解释为真正未文档化。“文档存在但未观察”统一保留静态来源，不能据此直接判为 `STALE`。

客户端 inventory 原始去重数为 170，其中 1 条 `PUT` path 实际是误扫入的 Go 函数代码，不是合法 URL，因此当前可用文档口径为 169。主管理后台文档口径为 561。客户端另观察到 7 个第三方接口，单独列示但不计入 194 个首方接口。

数据来源：

- `fat-client-interface-scan/results/fat-client-endpoint-summary.csv`
- `fat-admin-interface-scan/results/record-flow-kyc-page-action-endpoint.csv`
- `fat-admin-interface-scan/results/member-gap-merged-endpoint-summary.csv`
- `api/inventory/interfaces.csv`
