# ISOP-2032：接口契约评审

[验收用例](../test-cases.md) · [问题与决定](../questions.md) · [设计](../design.md) · [流程](../../workflow.md)

评审日期：2026-09-10。来源：本机 `/Users/rayleigh/API/FB`，接口文档版本 `69c9be0631a11b2f9ae08624dc5d9380c6069362`，相对 `365c785` 的10个提交。仅读取Git对象，未发业务请求；需求关联按内容推断。接口文档更新不等于部署完成。CoinPH不属于本期范围。

## 接口与验收对照

| 文档接口/范围 | 关联验收用例 | 已提供契约 | 缺口或验证边界 |
| --- | --- | --- | --- |
| GET（请求块）/POST（正文） /admin/promo/update | C05、C06 | 类型/指定游戏配置包含rate、upper_limit、lower_limit、multiple | 方法冲突；配置范围、精度和读回仍需确认 |
| GET /admin/promo/betting/rebate/report | C01—C04、C07—C10、C12、C13、C18 | 提供报表明细、total及conf规则详情 | 报表不能代替结算、入账和幂等执行证据 |
| GET /admin/promo/betting/rebate/export | C13 | 新增导出入口及topic_id | 待交付异步文件获取契约及真实Xlsx样本 |

## 后续实现

待确认项统一见问题文件：Q-11、Q-12、Q-13；原有未决问题继续有效。

可执行数据已生成于 [cases.json](cases.json)，执行方式与限制见 [API说明](README.md)。查询组合和鉴权/参数反例先执行；需专用写入样本、独立对账基准或尚缺正式契约的业务闭环逐条列为BLOCKED。执行证据按次写入本目录results，不覆盖P0报告；UI按[需求流程](../../workflow.md)接入专项自动化，尚未适配的部分由人工验收；查询PASS不自动变更整条验收状态。
