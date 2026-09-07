# ISOP-2037：合規後台 - 全平台投注紀錄增加欄位 — 测试设计

当前阶段：需求评审/测试准备；不代表业务测试通过。评审日期：2026-09-07（UTC+8）。

[可分派测试用例](test-cases.md) · [问题与决定](questions.md) · [批次评审](../review-summary.md) · [需求索引](../README.md)

## 来源与范围

- [Jira正文](https://alibaba-international.atlassian.net/browse/ISOP-2037)；创建：2026-09-05T00:16:03.986+0800；读取时最后更新：2026-09-07T10:44:40.005+0800；Story状态：待办（仅来源快照）。
- 子任务：[ISOP-2059](https://alibaba-international.atlassian.net/browse/ISOP-2059) [後端] 合規後台 - 全平台投注紀錄增加欄位；[ISOP-2060](https://alibaba-international.atlassian.net/browse/ISOP-2060) [前端] 合規後台 - 全平台投注紀錄增加欄位；[ISOP-2061](https://alibaba-international.atlassian.net/browse/ISOP-2061) [QA] 合規後台 - 全平台投注紀錄增加欄位。已读取子任务正文及评论，未见补充业务规则；状态不作为部署/验收证据。
- 范围：合规后台 > 游戏记录 > 全平台投注记录：四个 JP 字段、Multi 弹窗、JP Type 筛选及 CSV。
- 补充来源与关联：[原型](https://vip-admin-gray.vercel.app/pagcor-admin/game-records/all-plat-records)、[JP写入](../ISOP-2041/design.md)、[税报公式](../ISOP-2028/design.md)
- 读取边界：已只读查看 vip-admin gray 原型：24列表头和 JP Type 筛选可见，但列表为空，未获得 Multi 实际数据行为证据；原型仍有 Jackpot 菜单，这是2038的待改项，不据此判 FAT 缺陷。

## 验收依据

下表整理来源中明确的规则；推荐的可靠性/权限场景在用例中标示为测试设计。有歧义的部分以问题编号关联，不把建议当成已批准需求。

| 验收编号 | 业务预期 |
| --- | --- |
| AC-01 | GGR 后、结算时间前依次新增 JP Contribution、JP Payout、JP Type、Seed Money；提拨直接取已有金额显示4位，JP派彩显示2位。 |
| AC-02 | 仅 op、mi 有奖池；其他厂商四栏均为 -。有提拨未中奖：仅 Contribution 有值，其余三栏 -。单奖池类型 Mini/Minor/Major/Grand，Seed Money 取实际底金。 |
| AC-03 | GGR 保持投注金额−一般派彩，JP Payout 独立，不把2028税报公式套到该明细列。 |
| AC-04 | Multi 显示为链接并打开 Modal，不列内展开；含中奖池笔数、Transaction ID及各 JP Type/Payout/Seed Money，右上角和底部均能关闭；列表派彩为明细加总、Seed Money 为 -。 |
| AC-05 | JP Type 筛选含 Mini、Minor、Major、Grand、Multi。 |
| AC-06 | CSV 与列表完全一致，共24栏，表头逐字相符；无额外 JP 明细栏，Multi Seed Money 同样不显示。 |

## 测试分工与准备

准备 op/mi 单奖池与 Multi、其他厂商、低至0.0001的贡献、跨页数据和权限不同的合规账号。原始列 jp_contribution/jp_winning/seed_money/jp_type 已在2022只读查到，Multi明细存储仍待开发提供。

目标环境先以 FAT 准备；各端实际部署版本、接口路径/参数、账号角色与受控执行范围需在提测单核实。需求或原型可访问不代表功能已经部署。方法标为API/只读对账的用例需要实际接口返回和独立数据期望；不凭UI展示一致推定后端计算正确。

只有需求阶段先确认规则、盘点样本、冻结契约并分派用例；后端提测后先验证契约/业务状态/金额和异常副作用；前端提测后执行交互与跨端联调；最后对受影响模块回归。本需求暂不自动加入P0，不新增或复制runner。执行步骤及证据统一进入 [用例文件](test-cases.md)，讨论只更新 [问题文件](questions.md)。
