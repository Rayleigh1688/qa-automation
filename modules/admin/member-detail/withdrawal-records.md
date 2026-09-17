# 会员详情：提现日志

[逐页计划](plan.md) · [详情入口](README.md)

2026-09-17 13:51—13:52（UTC+8）FAT页面扫描及fresh API只读核验。无提现申请、审核、同步出款或导出。

## 页面与接口

筛选：三方订单ID、状态、提现金额、提现时间（这四组带下拉切换但本轮未展开）、渠道、备注、查询/重置；另有导出、刷新、密度/列设置。默认当日范围。列包含订单/三方单号、会员、状态、提现时间/金额/账户类型与ID、审核人/时间、到账时间/金额、手续费、服务商/渠道、来源域名、取消原因、备注、操作。当天为空，行内操作尚未发现。

汇总小计/合计列：提现订单数量、成功订单数量、提现金额、到账金额、手续费、支付失败数量。

契约来源api/catalog/admin/finance.csv及本机“后台/财务管理/提现记录/提现列表-wesley.bru”docs段。POST /admin/finance/withdraw/list，支持uid、id、status、external_order_id、account_id、channel_id、payment_method、phone、amount_min/max、start_time/end_time、page/page_size、comment、paid_start_time/paid_end_time、paid_amount_min/max、fee_min/max。时间文档描述模糊且示例13位，本轮毫秒查询有效，响应created_at亦13位毫秒。实际汇总在summary.sub_total/total，非文档字段表的a。

## 当前实测与待确认

指定配置会员，2026-08-18至09-17（UTC+8）窗口，page=1/page_size=20。HTTP200/status=true，总22条/首屏20条，首屏UID及创建时间均符合范围。状态为under_review 15、paying 2、canceled 3。首屏成功0，summary.sub_total的amount/paid_amount/fee均0，faild_order_total=3；全量合计成功0、amount/paid_amount/fee均0、faild_order_total=4。

业务口径缺口，按用户“有问题及时停下”停在此处，未判BUG或PASS：

1. “提现金额”只累加成功出款还是全部申请？当前无成功单汇总为0，文档只给字段名，无法推出正确范围。
2. “支付失败数量”是否包括取消？首屏3笔取消与失败计数3一致，只说明当前数据对应，不证明业务规则。

已集中询问用户以上两点，不把存款汇总成功口径直接套用提现。待答复后用完整两页重算及状态筛选核验。

证据在本地忽略路径`reports/qa/member-detail/20260917/withdrawals-readonly.json`，仅字段名/聚合与断言，不保存账户号码、姓名或认证信息。未测第二页、各筛选、汇总公式、审核/出款/取消关联、账户权限及导出；未进入礼金日志。

## 2026-09-17 用户确认与14:33实测

用户确认提现金额汇总仅统计成功提现，并要求核取消是否计入。此决定解决上文第1项；“支付失败数量”是否应包括取消仍没有单独业务确认。

扩大同一配置测试会员的只读窗口至2025-09-18—2026-09-17（UTC+8），以包含既有成功及取消样本；未申请或取消任何提现。POST /admin/finance/withdraw/list，uid、毫秒start_time/end_time、page=1/page_size=100。HTTP200/status=true，明细35条，data.t=35，同UID/时间范围符合、ID无重复。

状态分布：completed 3、canceled 13、paying 3、under_review 16。Decimal按成功明细重算amount=989、paid_amount=989、fee=0，均与summary.total一致；取消13条申请金额合计11828，未计入这些金额汇总。此样本支持用户成功口径，不代表所有状态转换及独立账变对账已完成。faild_order_total=13与取消数量相同，保留为实现观察。

新异常候选：同一次响应summary.total.order_total=36，但data.t及实际明细均35。脚本在订单数一致性断言处停止，后续canceled/completed独立筛选未执行；不能写成“取消筛选通过”。未重新查询，不确认根因，可能的汇总范围/并发等解释均待证据。

证据：本地忽略目录`reports/qa/member-detail/20260917/withdrawals-success-summary.json`；保留原断言失败。用户要求遇问题停下，当前停止在订单数量差异，不继续礼金日志。后续应固定同窗口核页面汇总及响应，确认多出的1单来源。
