# ISOP-2030：用戶端 - 遊戲頁面改版 — 测试设计

当前阶段：需求评审/测试准备；不代表业务测试通过。评审日期：2026-09-07（UTC+8）。

[可分派测试用例](test-cases.md) · [问题与决定](questions.md) · [批次评审](../review-summary.md) · [需求索引](../README.md)

## 来源与范围

- [Jira正文](https://alibaba-international.atlassian.net/browse/ISOP-2030)；创建：2026-09-03T18:37:08.862+0800；读取时最后更新：2026-09-07T10:45:13.208+0800；Story状态：待办（仅来源快照）。
- 子任务：[ISOP-2053](https://alibaba-international.atlassian.net/browse/ISOP-2053) [前端] 用戶端 - 遊戲頁面改版；[ISOP-2054](https://alibaba-international.atlassian.net/browse/ISOP-2054) [App] 用戶端 - 遊戲頁面改版；[ISOP-2055](https://alibaba-international.atlassian.net/browse/ISOP-2055) [QA] 用戶端 - 遊戲頁面改版。已读取子任务正文及评论，未见补充业务规则；状态不作为部署/验收证据。
- 范围：客户端游戏页改版，同时涉及一级页面 Header、Rewards、Filcoin、My；不能只测 Games。
- 补充来源与关联：[Lark来源](https://qsgpn7a1512s.sg.larksuite.com/wiki/VlmDw7Dk8iAlUOkDIcsl8o4Pgub)、[Figma定稿](https://www.figma.com/design/hyNW9tILDfjIjKO5WpRQYj/?node-id=145024-3487)
- 读取边界：已读取 Jira、Lark（2026-08-24更新）及 Figma Game 游戏260902画布：可见定稿四列游戏、Game Providers底部弹层和“新Header一级页面示意”。仅完成对应画布概览，未逐像素审完全部页面/主题。

## 验收依据

下表整理来源中明确的规则；推荐的可靠性/权限场景在用例中标示为测试设计。有歧义的部分以问题编号关联，不把建议当成已批准需求。

| 验收编号 | 业务预期 |
| --- | --- |
| AC-01 | Jira：登录后的一级页面固定Header，余额呈现逻辑不变；搜索/客服图标分别进入对应页面。 |
| AC-02 | Rewards删除标题；Filcoin删除客服图标，将Earn Filcoins/Filcoins Mall移到FAQ同一行；My的NEWS下移、其他选项删除（具体清单待确认）。 |
| AC-03 | Games调整分类和厂商入口，厂商logo横向滑动且全部可达，点logo筛该厂商游戏；游戏一行4个。 |
| AC-04 | All显示所有厂商入口；最终交互、默认选中状态按待确认项。Lark另提Favorites及最新收藏靠前，是否本版交付待确认。 |

## 测试分工与准备

当前按手工UI需求处理。2026-09-11核对：已保存提测消息仅为H5提测，未提供本需求API变更契约或后台提测依据；本批不安排独立API自动化。厂商筛选和余额通过页面联调核对，必要时查看已有请求辅助定位，不因此标为API变更。App场景仍待对应提测，视觉预期以已确认Figma版本为准。

目标环境先以FAT准备，但本条H5提测消息未明确环境；环境、H5版本、账号和已上线页面范围仍需核实。需求或原型可访问不代表功能已经部署。页面余额展示正确不代表后端计算已经完整验收。

当前先确认页面规则、盘点样本并分派人工用例；H5提测后执行交互与页面联调，再回归受影响页面。若后续补充了明确API变更，再单独评审并增加API用例，不预设每个页面改版都需要接口自动化。本需求暂不自动加入P0，不新增或复制runner。执行步骤及证据统一进入 [用例文件](test-cases.md)，讨论只更新 [问题文件](questions.md)。
