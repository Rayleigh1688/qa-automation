# ISOP-2028：接口增量评审

2026-09-11扫描。来源：本机backend_api及只读远端main核对，最新均为`b8daa7d7396716a767fb1e1bec567d7750a0253a`；相对上次`ca3c1c2`新增`cddc218 feat:doc`和`b8daa7d`合并提交。共5份Bruno文档，32行新增、1行删除，均为docs说明变化；未变更请求路径/方法。需求关联依据[2028设计](../design.md)的三类报表范围推断，提交没有需求编号，不视为提测或部署证据。

## 变更接口

| 接口（均POST） | 文档新增内容 | 关联用例 |
| --- | --- | --- |
| /cmpl/report/pagcor/list | totalGGR、totalJpContribution，均string，示例同步补充 | C01—C04、C08、C09 |
| /cmpl/report/pagcor/export | 导出列total GGR、total JP Contribution | C07 |
| /cmpl/report/shop/list | total_ggr、total_jp_contribution，响应示例和字段说明补齐 | C01—C03、C08、C09 |
| /cmpl/report/shop/export | 新增导出字段章节，列total GGR、total JP Contribution | C07 |
| /cmpl/report/summary/list | total_ggr、total_jp_contribution、total_jp_winning；说明为对应源字段SUM，示例同步增加 | C02、C03、C06、C08、C09 |

## 测试影响及未决项

- 新字段可作为后续结构、金额精度、筛选及列表/导出一致性断言的契约依据；Pagcor列表用驼峰、门店和摘要用下划线、导出表头带空格，不能用同一字段名套所有接口。
- 新total_ggr的生成公式仍未明确与需求`(有效投注−JP贡献)−(有效派彩−JP派彩)`如何对应；摘要沿用的ggr、payout_amount说明与新total_ggr并存，示例ggr=-403441.72、total_ggr=403441.72。不能仅凭示例判断新旧GGR必然取反，也不能把旧ggr直接当新卡片的预期。Q-02仍待源字段与独立金额样本核对。
- 本次没有补齐bet_type=1/3纳入、2排除的实现依据，亦未说明税率、舍入层级、完整导出列序、旧JP列移除和历史刷新完成情况；Q-03保持未决。没有新增时间参数，因此不能视为Q-01时间范围已澄清。
- 管理后台2022的`/admin/record/bet`、`/admin/record/game`在此增量中未修改。用户已要求2022等修复；不启动复测，也不凭文档无变化断言后端一定未修复。

## 接口资产同步

现有scanner重新离线扫描得到1149份Bruno资产、922条请求。此前inventory为1136份；差额13份来自累计未同步的旧提交，不能都计为这次2个提交的新接口。已刷新api/inventory和api/catalog；P0用例、候选池和门禁范围未扩大。新增资产中包括既有KYC复核、投注记录、返利及余额通知，CoinPH和临时调试请求仍仅属发现资产，不自动执行。

本轮只读Git与离线资产生成，未登录业务系统、未查库、未扫描Telegram、未执行API/UI、未建BUG或发群。当前尚无2028执行计划或本轮业务结果。
