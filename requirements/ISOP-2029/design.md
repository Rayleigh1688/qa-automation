# ISOP-2029：用戶端 - 免費旋轉領取文案調整 — 测试设计

当前阶段：需求评审/测试准备；不代表业务测试通过。评审日期：2026-09-07（UTC+8）。

[可分派测试用例](test-cases.md) · [问题与决定](questions.md) · [批次评审](../review-summary.md) · [需求索引](../README.md)

## 来源与范围

- [Jira正文](https://alibaba-international.atlassian.net/browse/ISOP-2029)；创建：2026-09-03T18:36:44.071+0800；读取时最后更新：2026-09-07T16:00:21.216+0800；Story状态：UAT 验收（仅来源快照）。
- 子任务：[ISOP-2056](https://alibaba-international.atlassian.net/browse/ISOP-2056) [前端] 用戶端 - 免費旋轉領取文案調整；[ISOP-2057](https://alibaba-international.atlassian.net/browse/ISOP-2057) [App] 用戶端 - 免費旋轉領取文案調整；[ISOP-2058](https://alibaba-international.atlassian.net/browse/ISOP-2058) [QA] 用戶端 - 免費旋轉領取文案調整。已读取子任务正文及评论，未见补充业务规则；状态不作为部署/验收证据。
- 范围：仅免费旋转领取成功弹窗文案/按钮；不改变发放次数或活动计算。
- 补充来源与关联：以 Jira 正文为主要来源。
- 读取边界：已审阅 Jira 文本与附件清单；未逐张人工核对所有截图，视觉细节需在提测时按最终稿复核。

## 验收依据

下表整理来源中明确的规则；推荐的可靠性/权限场景在用例中标示为测试设计。有歧义的部分以问题编号关联，不把建议当成已批准需求。

| 验收编号 | 业务预期 |
| --- | --- |
| AC-01 | 标题精确为 Free Spins Claimed!；内容两行：Your Free Spins are ready. / Start playing now or save them for later. |
| AC-02 | 按钮为 Play Later 和 Play Now；沿用既有稍后玩/立即玩行为，不因文案变更重复发放。 |

## 测试分工与准备

由客户端人员执行小范围文案回归即可，复用既有免费旋转数据和领取流程。子任务已有FAT/UAT状态仅作为排期线索，不能代替本轮执行结果。

目标环境先以 FAT 准备；各端实际部署版本、接口路径/参数、账号角色与受控执行范围需在提测单核实。需求或原型可访问不代表功能已经部署。方法标为API/只读对账的用例需要实际接口返回和独立数据期望；不凭UI展示一致推定后端计算正确。

只有需求阶段先确认规则、盘点样本、冻结契约并分派用例；后端提测后先验证契约/业务状态/金额和异常副作用；前端提测后执行交互与跨端联调；最后对受影响模块回归。本需求暂不自动加入P0，不新增或复制runner。执行步骤及证据统一进入 [用例文件](test-cases.md)，讨论只更新 [问题文件](questions.md)。
