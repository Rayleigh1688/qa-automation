# ISOP-2393 接口契约评审

[需求设计](../design.md) · [问题与决定](../questions.md) · [接口测试草案](test-plan.md)

2026-11-27 核验 FB Bruno 本地提交对象和远端 `main`，两者均指向 `f73f349`。本次提交范围从 `3f2ba83` 到 `f73f349`，共 4 个文档文件、3 条不同接口路径、4 项操作。后端实现仓库和 FAT 版本尚未核实。 [GitLab 提交对比](https://git.filbet2025.com/api_doc/backend_api/-/compare/3f2ba835917f2040b9e32bffe1949cea36fce72d...f73f349b4dc34d1a085a35fd45c4674b650b7853)

## 提交明细

| 提交 | 方法与路径 | 文档增量 |
| --- | --- | --- |
| [d0e0d5a](https://git.filbet2025.com/api_doc/backend_api/-/commit/d0e0d5a4510e6a16bc3e200c8ec0a5d30beadb1a)、[8fe13f0](https://git.filbet2025.com/api_doc/backend_api/-/commit/8fe13f070a5fe37150260d88babc894138fe3a23) | `GET /member/detail` | 第一笔新增 `daily_bet_amount` 整数示例，后一笔改为金额字符串并新增秒级 `edit_countdown`。两字段均位于既有 `data.exclusive_info`。 |
| [22ade96](https://git.filbet2025.com/api_doc/backend_api/-/commit/22ade96db1c187ef533b23064cb7599afa207b9f) | `GET /admin/member/limitation/state/info?uid=…` | 新增 `data.exclusive_info` 及 `data.exclusive_info_list`，原通用限制查询保留。 |
| [f73f349](https://git.filbet2025.com/api_doc/backend_api/-/commit/f73f349b4dc34d1a085a35fd45c4674b650b7853) | `POST /admin/member/limitation/info/update` | 新增设置／修改和取消两个 Bruno 模板。两模板均写 `body: none`，请求参数仅列在说明。 |
| [65d65e5](https://git.filbet2025.com/api_doc/backend_api/-/commit/65d65e5da1574596269943892148f00dbdbf6918)（同日较早） | `POST /member/exclusive/info` | 会员保存。说明要求 CBOR，包含 `bet_switch` 和金额字符串 `limited_bet_amount`。 |

## 能力与契约差异

| 能力 | 当前契约与断言 | 缺口与影响 |
| --- | --- | --- |
| 会员状态 | 会员详情最终示例 `bet_switch` 为 `0`／`1`，`limited_bet_amount`、`daily_bet_amount` 为字符串，`edit_countdown` 为剩余秒数。对同一会员核对开关、金额与有效锁定时间；金额用 Decimal，保留原始字段类型。 | 详情示例有 JSON 逗号错误。关闭状态空值及倒计时语义待确认。既有 [P0 `TC-001`](../../../api/p0/test-cases.csv) 只断言会员基础字段。A01、A07。 |
| 后台状态 | 以 `uid` 定位。新增 `bet_switch`、`limited_bet_amount` 和毫秒级 `operator_time`。核对后台和会员详情读回同一站点、同一会员的状态。 | 后台 `limited_bet_amount` 示例为 `true`，缺实际金额类型、空值和设置来源枚举。保留原限制字段的兼容检查，参考 [2026-09-17 无锁基线](../../../modules/admin/member-detail/security-restrictions.md#接口契约与实测差异)。A02、A04。 |
| 后台审计 | `exclusive_info_list` 示例含秒级 `created_at`、`change_type`（`18` 修改、`19` 取消）、`operator`、`reason`、`before_amount`、`after_amount`。分别按各自单位换算 UTC+8 时间。 | 缺来源、首次设置映射、取消空值及分页契约。文档 GET 只列 `uid`，每页 10 笔可能由页面处理，待确认后绑定断言。A06。 |
| 后台写入 | 设置示例含 `uid`、`bet_amount`（金额字符串）、`note`。取消示例含 `uid`、`is_cancel`、`note`。两种操作示例为 `status: true`、`data: "ok"`。 | 取消示例 `is_cancel: 0` 与 `1` 表示取消的旁注相冲突；确认取消枚举、请求编码、独立编辑权限及业务拒绝码后再做受控写入。A04、A05、A10。 |
| 会员写入 | CBOR 文档描述 `bet_switch` 的 `0` 为关、`1` 为开。按当日锁定判定有效写入和拒绝，双端读回并对照历史。 | 文档写成功／失败为 `code: true`／`false`，成功 `data` 示例存在格式问题。与后台写入的 `status` 示例分别核对真实信封、关闭时金额传法与锁定拒绝码。两个 GET 文档的业务结果示例也是 `code`，先验证实际解码结果。A01—A03、A07、A10。 |
| 游戏准入 | 现有仓库 [MF-004／MF-005](../../../api/p0/main-flow-scenarios.csv) 提供真实游戏和投注记录的核验方式。 | 四笔提交没有修改游戏入口或统计接口文档。需要确认实际入口、拒绝结果和会员日统计刷新证据，按两站分别验收。A08、A09。 |

两个 GET 适合作为首批 FAT 只读用例。后台设置、取消和会员保存需要独立的当轮专用会员、受控执行范围和读回检查。旧 `POST /admin/member/limitation/state/update` 对应通用功能锁。游戏入口和统计联测依赖对应站点的 FAT 版本及可追溯数据。截至本次评审，三种范围均待实测。
