# ISOP-2028：合規後台 - 統計數據時間調整 — 测试设计

当前阶段：需求评审/测试准备；不代表业务测试通过。评审日期：2026-09-07（UTC+8）。

[可分派测试用例](test-cases.md) · [问题与决定](questions.md) · [批次评审](../review-summary.md) · [需求索引](../README.md)

## 来源与范围

- [Jira正文](https://alibaba-international.atlassian.net/browse/ISOP-2028)；创建：2026-09-03T18:31:21.495+0800；读取时最后更新：2026-09-07T10:45:18.109+0800；Story状态：待办（仅来源快照）。
- 子任务：[ISOP-2047](https://alibaba-international.atlassian.net/browse/ISOP-2047) [後端] 合規後台 - 統計數據時間調整；[ISOP-2048](https://alibaba-international.atlassian.net/browse/ISOP-2048) [前端] 合規後台 - 統計數據時間調整；[ISOP-2049](https://alibaba-international.atlassian.net/browse/ISOP-2049) [QA] 合規後台 - 統計數據時間調整。已读取子任务正文及评论，未见补充业务规则；状态不作为部署/验收证据。
- 范围：合规后台报表中心：Pagcor税收报表、门店税收报表、报告摘要的JP统计与GGR；标题“时间调整”与正文内容不一致。
- 补充来源与关联：[合规FAT](https://admin-pagcor-fat.filbet2025.com)、[JP写入](../ISOP-2041/design.md)、[明细不同GGR](../ISOP-2037/design.md)
- 读取边界：已审阅 Jira 文本与附件清单；未逐张人工核对所有截图，视觉细节需在提测时按最终稿复核。

## 验收依据

下表整理来源中明确的规则；推荐的可靠性/权限场景在用例中标示为测试设计。有歧义的部分以问题编号关联，不把建议当成已批准需求。

| 验收编号 | 业务预期 |
| --- | --- |
| AC-01 | 两张税报Onsite/Online的JP投注改为JP贡献，取jp_contribution期间加总，与2037同来源，不是JP游戏投注额。 |
| AC-02 | 新GGR=(有效投注−JP贡献)−(有效派彩−JP派彩)；有效投注/派彩及jp_contribution/jp_winning均只统计bet_type=1,3，排除2。适用于两税报对应GGR及摘要GGR卡。 |
| AC-03 | Pagcor Onsite/Online有效税收=新GGR×税率；两税报删除各自旧JP盈亏/JP GGR列，Onsite和Online同步。 |
| AC-04 | 摘要GGR后新增JP贡献总额、JP派彩总额卡，沿用Pagcor分类和日期筛选；仅mi/op有奖池，其余JP指标显示0.00。 |
| AC-05 | 两税报GGR标题后加info并hover展示新公式；导出列与列表一致，改名/删除之外其余列顺序不变。 |

## 测试分工与准备

目标环境正文明确为PAGCOR FAT。使用同一组已知一般派彩/JP/贡献样本联动2041、2037；税率从实际配置只读取得，QA不直接重算生产或写库。

目标环境先以 FAT 准备；各端实际部署版本、接口路径/参数、账号角色与受控执行范围需在提测单核实。需求或原型可访问不代表功能已经部署。方法标为API/只读对账的用例需要实际接口返回和独立数据期望；不凭UI展示一致推定后端计算正确。

只有需求阶段先确认规则、盘点样本、冻结契约并分派用例；后端提测后先验证契约/业务状态/金额和异常副作用；前端提测后执行交互与跨端联调；最后对受影响模块回归。本需求暂不自动加入P0，不新增或复制runner。执行步骤及证据统一进入 [用例文件](test-cases.md)，讨论只更新 [问题文件](questions.md)。
