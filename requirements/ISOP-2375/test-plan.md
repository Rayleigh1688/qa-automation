# ISOP-2375：综合验收测试计划

[接口执行入口](api/README.md) · [需求设计](design.md) · [验收场景用例](test-cases.md) · [原子接口用例](api/test-cases.md) · [接口用例 JSON 审阅稿](api/test-cases.review.json) · [待确认事项](questions.md) · [总用例表](cases.csv)

Jira 的 17 项改动落在 **16 条会员端接口路径**。其中两项改动共用 `/member/detail`。加上 A04 的站内信弹窗对照，验收共 **17 条会员端路径**。A07 的后台页面是回归对照，按各页面现行业务请求核对操作人展示。

## 接口范围

| 验收项 | Jira 修改项 | 会员端接口路径 | FAT 原子用例 |
| --- | --- | --- | --- |
| A01 匿名读取（11） | 1—5、7、8、10—12、14 | `/promo/list`、`/promo/task/newbie/daily`、`/promo/task/daily/task`、`/member/game/list/recommended`、`/member/buriedPoint/detailV2`、`/member/v2/index`、`/member/game/listRw`、`/promo/turntable/detail`、`/promo/task/newbie/list`、`/promo/task/daily/list`、`/member/vip/rule` | [C09—C23](api/test-cases.md#c09)，首页四品牌各一条，日常签到两个返回分支各一条 |
| A02 会员登录读取（3） | 6、9、13 | `/finance/payment/bank/list`、`/member/game/list/recommend`、`/promo/vip/config` | [C24—C26](api/test-cases.md#c24) |
| A03 站内信列表（1） | 15 | `/member/message/list` | [C27](api/test-cases.md#c27) |
| A05／A06 会员详情（1） | 16、17 | `/member/detail` | [C29、C30](api/test-cases.md#c29)，已设钱包密码与三方登录分别使用各自的测试样本 |
| A04 回归对照（1） | — | `/member/message/popup_list` | [C28](api/test-cases.md#c28) |

共 **22 条 FAT 原子用例**。每条独立列出请求方法、地址、参数、样本及断言。接口覆盖按不同路径计，场景覆盖按实际执行的品牌、分支和账号状态计。A01 对应版本上线后，用正式站的实际配置与样本复核适用路径。

## 综合验收场景

| 场景 | Jira 验收项 | 组合证据与通过条件 |
| --- | --- | --- |
| 匿名访问首页及活动 | A01、A08 | C09—C23 的匿名读取命中有效数据，员工字段符合清理规则。四品牌首页与导航正常，会员端活动、签到、任务、转盘与 VIP 规则可正常打开并使用对应入口。详见 [C01](test-cases.md#c01)、[C08](test-cases.md#c08)。 |
| 登录后关键读取及后台对照 | A02、A07、A08 | C24—C26 的银行、游戏推荐与 VIP 配置正常返回，后台人员字段清理符合预期。用同一银行证明后台仍显示操作人，同时回归后台活动、任务、游戏、埋点和转盘的操作人，以及会员端银行选择、推荐和 VIP 展示。详见 [C02](test-cases.md#c02)、[C07](test-cases.md#c07)、[C08](test-cases.md#c08)。 |
| 后台发信与会员阅读 | A03、A04、A07、A08 | 后台给测试会员定向发送或选用已存在的受控样本，记录消息标识和后台人员展示。列表和弹窗分别命中对应消息，人员字段均须缺失、为 `null` 或为空字符串。会员端正文、列表和弹窗正常。详见 [C03](test-cases.md#c03)、[C04](test-cases.md#c04)。 |
| 钱包与三方登录回归 | A05、A06 | C29 严格保留已设置钱包密码的状态，并用该请求 ID 关联日志确认无密码数据。C30 使用通过三方登录的样本，清理授权字段且保留三方类型和名称。详见 [C05](test-cases.md#c05)、[C06](test-cases.md#c06)。 |

## 执行顺序与判定

1. **准备版本与样本。** 核对 FAT 的 member、promotion、finance 版本。盘点活动、任务、首页、埋点、游戏、银行、VIP 和消息的可见样本，记录同一业务对象的标识及需要保留的业务字段。另准备钱包及三方测试会员，以及 A05 的日志读取条件。见 [Q-03、Q-04](questions.md#q-03)。
2. **先做修改接口的基础契约测试。** 按接口文档及已有资产逐条构造 16 条修改路径的原子请求，另跑站内信弹窗对照。每行发一次请求，将 HTTP、解码、业务成功、结构、样本命中和该用例的目标字段要求一起判定。每条用例出一个结果，并记录具体不符合的条件。`/promo/list`、品牌路由和任务分支按各自缺口补齐。见 [Q-06—Q-08](questions.md#q-06)。
3. **合并验收证据。** 用原子结果、前后台同一记录的对照、页面交互结果及对应服务日志核对 A01—A08。样本缺失、品牌或分支无法辨认、日志无法关联时，记录该项未覆盖及具体原因。有效样本触发字段不符、合法业务字段丢失或页面行为回归时，按对应验收项报告失败。
4. **上线后确认。** 按发布流程只读复核 A01 对应的正式站请求。A05／A06 列入测试计划，其是否作为上线阻塞由 Q-04 确认。原报告接口范围待 Q-05 确认。

## 数据驱动能力与接入状态

参考本机 `web-ddt-main` 的两种表驱动方式。`pythonProject/testcase/test_login.py` 用 CSV 的输入和期望值参数化同一登录测试，每行独立判定。`pythonProjectweb_232/conftest.py` 按 Excel 的关键字和参数执行浏览器步骤，一组步骤组成一个 UI 用例。2375 借鉴前者组织原子接口数据，综合验收按后一种思路组合场景证据。

| 入口 | 已有能力 |
| --- | --- |
| P0 CSV | 执行器读取每行的接口方法、URL、请求体与断言。已有首页、组合游戏、登录推荐、银行、会员详情和后台银行对照可复用。 [P0 用例资产](../../api/p0/test-cases.csv) |
| 需求 `plan.json` | `datasets` 提供可复用数据集，通过变量绑定请求和断言。执行时展开并保留每组的执行编号和独立结果，支持 `--only` 定向选择，`api/data-cases.csv` 是生成的评审表。 [历史配置示例](../history/through-ISOP-2072/ISOP-2027/plan.json) · [执行能力记录](../../docs/new-requirement-stage1-2.md) |
| 2375 | 完整验收设计放在 JSON 审阅稿。`api/test-cases.json` 保存已备齐的 13 条只读响应检查。命令由供测试的客户端 FAT 会话执行。 [Python 指令](api/README.md) · [执行用例](api/test-cases.json) · [数据集](api/datasets.yaml) |

落入数据集的是分页、活动和广告标识、品牌入口、会员样本及预期业务值。以银行列表为例，固定 GET 路由与通用字段断言，只让数据集提供 `bank_page` 和预期银行 ID。同一个请求模板每次绑定一个明确样本，独立记录基础契约和敏感字段结果。

## 2026-11-27 FAT 执行 A01–A06

使用 `.venv/bin/python scripts/run-requirement.py ISOP-2375 --env .env.fat` 的定向执行入口。常规会员和已设钱包密码的提现测试会员分别登录，业务请求均为只读 GET。普通批次 `20261127T081815Z-e1b469a1`，钱包批次 `20261127T081814Z-6b47c6ed`。部署版本未提供。两批合计 **10 PASS、4 FAIL、10 NOT_RUN**，计数为本批检查结果。

| 验收项 | 实测及待验证内容 |
| --- | --- |
| A01 | 7 条基础响应检查通过。C23 VIP 规则的 `updated_uid` 触发空值断言失败。随后复核到 31 个值均为整数 `0`，未观察到有效 UID，原 FAIL 保留，零值契约待确认。C09、C11、C12、C14、C15—C18、C20 仍缺请求契约、分支、品牌或业务样本。 |
| A02 | C24 银行列表本页字段检查通过，指定银行的后台操作人样本待核。C25 推荐列表业务成功但 `data.d` 为 `null`，非空样本断言失败。C26 VIP 配置复核到 31 个 `updated_uid` 均为整数 `0`，空值口径与 C23 相同。 |
| A03 | C27 现有会员站内信的返回结构与人员字段断言通过。指定消息的发送和样本关联未覆盖。 |
| A04 | C28 弹窗返回有效消息，`trigger_person`、`maintainer` 键均存在。该批按当时脚本的严格缺失断言判 FAIL。证据只记录键名。 |
| A05 | C29 钱包详情响应通过，`has_wallet_password=true` 保留，`wallet_password` 满足清理断言。FAT 服务日志的访问与请求关联证据仍缺。 |
| A06 | C30 未执行，缺可确认的三方登录会员及独立展示样本。 |

VIP 复核只记录值类别及计数，单独保存在主批次的 `vip-uid-observations.json`，未覆盖两条原始失败。A07、A08 不在本轮范围。

断言修订后，C23、C26 的 `updated_uid` 均接受整数零。C23 依据同日 FAT 复核，正式契约待确认。C26 依据 [FB 文档更新](https://git.filbet2025.com/api_doc/backend_api/-/commit/c2a1dc2aa00462ce74086f404ae5592649f0fb38)。修订后的接口结果等本轮复跑，见 [定向执行命令](api/README.md#执行)。

## 2026-11-27 FAT 弹窗响应复判

18:18（UTC+8）批次 `20261127T101853Z-63534959` 的 C28 响应共 151 条记录。`trigger_person` 与 `maintainer` 各出现 151 次，均为空字符串。按用户确认的 [A04 口径](design.md#明确验收规则)，用该批 HTML 留存的完整响应离线执行新版 C28 的四条断言，全部通过。原批次报告保留当时严格缺失断言的 FAIL。指定消息样本及弹窗页面展示按综合用例单独验收。
