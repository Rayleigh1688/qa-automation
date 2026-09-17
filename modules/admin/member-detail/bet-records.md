# 会员详情：注单明细

[逐页计划](plan.md) · [详情入口](README.md)

2026-09-17 13:23—13:24（UTC+8）FAT页面扫描与fresh只读API核验，无新增投注、回调或重结算；未恢复暂停的体育2022专项。

页面筛选：注单ID、状态、注单类型、游戏类型、游戏名称、金额范围、线路、时区、时间范围、查询/重置。默认UTC+8、当日投注时间。金额/时间带切换菜单，本轮未展开，不将其他选项当已扫描。列表展示注单ID、会员账号/手机、游戏名称、投注时间、状态/类型、场馆/厂商、投注金额、来源域名、投注详情、结算时间、开奖结果、有效投注、派彩、GGR、JP中奖。小计/合计包括单数、投注、有效投注、派彩、GGR、JP。当天UI为空，不能验证行内投注详情。

契约来源：api/catalog/admin/finance.csv及本机“后台/财务管理/注单管理/游戏记录-wesley.bru”docs段。POST /admin/record/bet，投注start_time/end_time或结算settle_start_time/settle_end_time为毫秒；id查询bill_no，状态优先state。文档说明普通/免费旋转/JP/红利及体育副本查询规则，当前只测普通已结算样本，不推广结论。

实测查询2026-09-16完整一天、指定配置会员、page=1/page_size=20：HTTP200/status=true，1笔已结算，UID及投注时间匹配；投注100、有效投注100、派彩0、GGR100、JP0，小计和合计同值。明细满足bet_amount - payout_amount = net_amount（该接口net_amount是展示GGR，不能套用原始库玩家输赢符号）。注单号及state筛选均非空且命中对应记录。

证据本地忽略目录：`reports/qa/member-detail/20260917/bets-readonly.json`。金额公式用Decimal；小计/合计为返回值核对，不是独立数据库或三方对账。

未测：其他类型/状态、线路/时区切换、金额与时间边界、分页、非空行内详情、权限、体育/JP计算、三方原单。无新异常，继续存款日志；不宣称整页通过。
