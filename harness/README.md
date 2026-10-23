# Harness 排障索引

Harness 记录测试为什么失败、如何定位以及哪些现象属于已知环境或产品问题。它不定义 P0 范围，也不保存实时执行进度。

## 按现象进入

| 现象 | 先读 | 继续进入 |
| --- | --- | --- |
| HTTP 200 但业务失败、登录/token/CBOR/runner 调试 | [`api-debug.md`](api-debug.md) | [`known-errors.md`](known-errors.md)、[`api/runbooks/API.md`](../api/runbooks/API.md) |
| 页面打不开、定位失败、弹窗、登录、iframe/canvas、固定视口 | [`ui-debug.md`](ui-debug.md) | [`ui/README.md`](../ui/README.md) |
| 账号前置、KYC/流水/钱包/充值/提现落库状态 | [`database-debug.md`](database-debug.md) | [`api/p0/README.md`](../api/p0/README.md) |
| 已确认重复出现的产品或 FAT 环境异常 | [`known-errors.md`](known-errors.md) | 对应 API/UI/DB 调试页 |
| 偶发失败、重试后恢复、需要统计触发条件 | [`flaky-tests.md`](flaky-tests.md) | 稳定复现后移入 `known-errors.md` |
| 流量上涨容量准备、生产监控／日志、接口或报表定位 | [分模块 HTML 报告](../testing-plan/observability-capacity-report-2026-10-19.html) | 固定七天排17。已收敛首批补监控对象，未闭合全部根因：Game资金链／登录优先补span，再覆盖高频与既有错误路径、后台查询；全请求指标与采样trace分开，真实Game handler及服务映射待核。新增RW局部约束：15日七compute Pod同刻CPU最高约51.36核，compute-2受限CFS周期采样约59%—95%，18:05—18:17采样已高，不当算力损失比例或回填致因。先核每Pod配额／节流、任务阶段与最终新鲜度；同名BI sink已区分内部dev／uat，不据此判重复浪费。HTTP错误、CPU聚合与Game分母等边界见[技术记录及计划](../testing-plan/07-可观测性与性能定位.md#七天排17的跨平台均衡分析2026-10-19)。不据全群均值保证3倍容量或换算报价；生产只读、账号调查暂停、监控未部署 |

## 记录规则

1. 先记录现象、发生条件、影响范围、最小复现和当前处理，不先放宽断言。
2. 临时观察留在 Harness；确认成为执行规则后，提升到 runbook、`skills/` 或 `api/p0/`，Harness 只保留故障表现和排查入口。
3. 当前放行状态和下一步只更新 [`AI-HANDOFF.md`](../AI-HANDOFF.md)，避免排障记录变成第二份交接文档。
4. 不记录真实凭据、token、cookie、TOTP seed、设备 ID 或未脱敏个人资料。

## 问题记录模板

新增或更新问题使用：问题 ID、适用环境、首次/最近验证日期、状态（待确认/活跃/已修复/范围排除/历史）、影响用例、最小复现、当前处理、证据位置。历史处理标记失效日期；环境接受标准链接到环境手册，不在故障页另定放行规则。
