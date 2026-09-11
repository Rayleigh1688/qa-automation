# ISOP-2027：接口契约评审

[验收用例](../test-cases.md) · [问题与决定](../questions.md) · [设计](../design.md) · [流程](../../workflow.md)

评审日期：2026-09-10。来源：本机 `/Users/rayleigh/API/FB`，接口文档版本 `69c9be0631a11b2f9ae08624dc5d9380c6069362`，相对 `365c785` 的10个提交。仅读取Git对象，未发业务请求；需求关联按内容推断。接口文档更新不等于部署完成。CoinPH不属于本期范围。

## 接口与验收对照

| 文档接口/范围 | 关联验收用例 | 已提供契约 | 缺口或验证边界 |
| --- | --- | --- | --- |
| POST /admin/kyc/edit | C01—C05、C15 | 编辑文档增加attachments | 待确认编码、附件结构与隔离测试数据 |
| POST /admin/kyc/review | C06—C11、C16 | id、reason、review_status（1待复核/2核准/3驳回） | 本人不能自审等业务规则必须独立验证 |
| 分行变更联动游戏类型限制（接口映射待补） | C18 | 远端1fb6d54新增AC-03/C18；尚需目标分行配置、限制读取及同步规则 | 原人工通过记录保留；现有分行字段读写断言不覆盖游戏限制，当前计划未实现C18 |
| GET /admin/kyc/review/list | C12、C13 | state、review_status及提交人/时间/会员筛选 | 待核对分页、计数与字段diff |
| GET /admin/kyc/ekyc/log；POST /admin/kyc/list | C01、C14、C15 | 更新异动记录及KYC列表文档 | 审计追加、正式资料保护不能仅检查HTTP成功 |

## 后续实现

待确认项统一见问题文件：Q-04；原有未决问题继续有效。

当前完整执行配置维护于plan.json，[cases.json](cases.json)保留查询兼容，执行方式与限制见[API说明](README.md)。需专用写入样本、独立对账基准或尚缺正式契约的业务闭环逐条记录缺口。统一执行证据在reports/qa，本目录results仅为旧查询入口，不覆盖P0报告；新需求UI按[需求流程](../../workflow.md)人工验收。查询PASS不自动变更整条验收状态，远端人工状态也不改写自动结果。

2026-09-10另重读本单Jira正文与评论（更新时间2026-09-09T16:33:48.173+0800，评论为空），核对既有验收设计。

## 2026-09-11执行资产迁移核对

权限准备使用的后台账号列表：Bruno旧契约GET /admin/user/list实测405；当前FAT公开前端assets/umi-dc472f73.js明确声明POST同路径、body参数。已将确认的只读POST契约纳入plan.json。该脚本本轮读取SHA256：`47d0cd2d3324b865f25e5beb90dfc0c1f04afef01145ce5df121db90113ee358`。前置读取失败期间未撤权，失败记录保留。
