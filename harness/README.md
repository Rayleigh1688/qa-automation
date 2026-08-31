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

## 记录规则

1. 先记录现象、发生条件、影响范围、最小复现和当前处理，不先放宽断言。
2. 临时观察留在 Harness；确认成为执行规则后，提升到 runbook、`skills/` 或 `api/p0/`，Harness 只保留故障表现和排查入口。
3. 当前放行状态和下一步只更新 [`AI-HANDOFF.md`](../AI-HANDOFF.md)，避免排障记录变成第二份交接文档。
4. 不记录真实凭据、token、cookie、TOTP seed、设备 ID 或未脱敏个人资料。
