# ISOP-2100：2026-10-05 缺陷提交记录

用户明确要求“把这四个BUG都提出来先”。以[本期需求核查](acceptance-20261005.md)确认的 F01、F05、F08、F09 为提交范围；沿用10月5日接口与只读源证据，没有新增业务执行。

## 提交结果

| 本地编号 | Jira | 问题 | 本次操作 | 后端关联 |
| --- | --- | --- | --- | --- |
| F01 | [TEST-3221](https://alibaba-international.atlassian.net/browse/TEST-3221) | 代理响应仍含完整手机号及IP | 查重命中既有单，补齐原空描述和需求关联 | ISOP-2150 |
| F05 | [TEST-3227](https://alibaba-international.atlassian.net/browse/TEST-3227) | NGR小计不等于当页明细合计 | 新增 | ISOP-2166 |
| F08 | [TEST-3228](https://alibaba-international.atlassian.net/browse/TEST-3228) | 总计只对应单代理，未覆盖全部符合条件代理 | 新增 | ISOP-2166 |
| F09 | [TEST-3226](https://alibaba-international.atlassian.net/browse/TEST-3226) | 活动彩金少计189.47，部分错归无代理，NGR偏高 | 新增 | ISOP-2166 |

四单均关联[ISOP-2100](https://alibaba-international.atlassian.net/browse/ISOP-2100)，提交后回读状态均为待办、优先级高、经办人Bali、QA为ukr。F01保留既有标题、经办人与QA；另外三单按报表后端任务负责人设置。状态仅代表10月5日提单后快照，不代表已修复或复测通过。

## 查重与描述边界

- F01与既有TEST-3221一致，采用补齐描述而非重复建单；仅已确认手机号和IP非空样本，未把其他个人字段当作已经复现。
- TEST-3219为另一账号的投注数据漏统；TEST-3220为管理会员日统计数据隔离。F09按已领活动的金额与代理归属独立登记，未覆盖旧单或推断共同根因。
- F05用同响应明细独立求小计；F08用完整四代理明细求总计，均不借用另一个错误汇总作为预期。
- F09采用最新正文复评：Bonus应191.47、实际2，NGR应−101.73、实际87.74。排行榜150错误归属与返利39.47遗漏分别陈述，未假定同一根因。
- 工单含复现参数、需求依据、预期／实际及可人工复算数值；仅使用测试别名和定位UID，不附手机号、IP原值、凭据或token。未上传原始响应或补造页面截图。

## 验证与留档

通过Jira独立回读，逐单核对标题、完整描述、状态、优先级、经办人、QA、主需求及后端任务关联。新增3单、复用1单；[本地回读留档](../../reports/qa/ISOP-2100/20261005-jira-delivery/verified-delivery.json)包含提交映射及逐项检查结果。

本期HTML和问题清单同步单号。业务证据仍为10月5日已执行批次，页面／导出边界沿用原报告；提单阶段未重新测试业务、变更数据库或发送群消息，后续群同步见下节。

本地 `npm run check:docs` 通过（262份文档），相关 `git diff --check` 通过；仅有既有CSV换行符提示。未运行资金门禁或把文档检查当成缺陷复测。

## 提单后群同步

10-05用户明确：已提Jira的BUG汇总应发到 **filbet提测发布群**（配置 `submission_chat_id`），不是 **FILBET 测试部**（`testing_chat_id`）。已用既有连接器发送一条包含4个单号、问题摘要及链接的汇总；用户随后明确确认消息发送成功，没有重发或向测试部群发送。

Telegram接受请求后的本地响应断言失败，原始回执及消息ID未保存；不补造消息编号。送达依据为用户确认，记录见[群同步状态](../../reports/qa/ISOP-2100/20261005-jira-delivery/telegram-delivery-status.json)。本批没有经过旧队列的 `approve/submit`，未改队列、扫描游标或其他待办。后续日常流程与旧CLI差异统一见[Telegram交付说明](../../docs/telegram-qa.md)。
