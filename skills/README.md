# 测试 Skills 索引

本目录保存项目长期有效的测试方法和业务判断，不保存当前执行进度、账号状态或临时环境故障。

Codex 可自动发现的正式项目 Skill 位于 [`.agents/skills/filbet-p0-automation/SKILL.md`](../.agents/skills/filbet-p0-automation/SKILL.md)。正式 Skill 只负责按任务路由；下列文档负责具体方法。

| 文档 | 解决的问题 | 下一层 |
| --- | --- | --- |
| [`api-testing.md`](api-testing.md) | API 用例准入、断言、runner 和受控写边界 | [`api/p0/README.md`](../api/p0/README.md)、[`api/runbooks/API.md`](../api/runbooks/API.md) |
| [`ui-testing.md`](ui-testing.md) | Playwright 分层、定位、Network 和结果规则 | [`ui/README.md`](../ui/README.md)、[`harness/ui-debug.md`](../harness/ui-debug.md) |
| [`business-rules.md`](business-rules.md) | 主流程顺序、业务通过标准、账号与资金规则 | [`api/p0/README.md`](../api/p0/README.md) |

## 信息边界

- 当前进度、最新证据、阻塞和下一步：只看 [`AI-HANDOFF.md`](../AI-HANDOFF.md)。
- 失败现象、环境差异和调试记录：进入 [`harness/README.md`](../harness/README.md)。
- P0/P1/P2 边界和阶段验收：进入 [`testing-plan/00-测试自动化总体规划.md`](../testing-plan/00-测试自动化总体规划.md)。
- 自动生成报告只能作为最近一次证据，不能反向覆盖本目录的长期规则。

新增规则时先判断它是否跨多条用例长期成立；一次性观察应先进入 Harness，稳定复现并影响测试决策后再提升到本目录。
