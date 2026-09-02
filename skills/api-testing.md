# API Testing Skill

## 用途

指导 AI 或测试执行者维护、扩展和执行本项目的 API 自动化资产。

适用范围：

- 从 Bruno 接口文档生成接口清单。
- 从接口清单筛选 P0/P1 候选接口。
- 维护客户端、后台 P0 API 用例。
- 执行 smoke runner 并生成 Markdown 报告。
- 判断接口是否可以进入自动化门禁。

## 规则

1. 先读 `api/runbooks/API.md`。涉及环境差异时读 `api/runbooks/ENVIRONMENTS.md`；如果处理后台接口，再读 `api/runbooks/ADMIN.md`。
2. 接口文档只负责发现接口，不能直接决定用例价值。新增接口必须先映射到 `api/p0/main-flow-scenarios.csv` 的业务场景。
3. P0 统一管理在 `api/p0/`：
   - 用例：`api/p0/test-cases.csv`
   - 场景：`api/p0/main-flow-scenarios.csv`
   - 说明：`api/p0/README.md`
   - 报告：`api/results/*.md`、`api/results/*.json`、`api/results/*.html`
   - 只包含 API 资产和 API 执行结果；UI 报告和结果必须放在 `ui/reports/`、`ui/results/`，不得写入 `api/results/`。
4. 每条用例不能只看 HTTP 200，至少要断言：
   - 响应可解码。
   - 业务结果符合预期：正例为 `status=true`；反例为明确拒绝或受控降级，且不产生不应有的副作用。
   - `data` 类型符合预期。
   - 关键字段存在。
5. FAT 当前使用 CBOR 请求/响应，runner 执行时使用 `--body-format cbor`。
6. FAT 当前本机证书链需要临时 `--insecure`，只允许用于测试环境。
7. 真实账号、OTP、Google code、token、cookie、设备 id 只能通过环境变量或 CI secret 注入，不写入仓库。
8. `api/results/*.json` 是最近一次 API 原始执行结果，每次覆盖刷新，不做历史累计，且不提交。
9. `api/results/*.md`、`api/results/*.html` 是 API 可读结论，每次覆盖刷新，不提交；同名 CSV 说明 Markdown 不再保留。
10. 执行 API 套件优先使用 `python3 scripts/run-api-tests.py <level...>`，不要直接散跑底层脚本；统一入口会先清空 `api/results/` 再写入本次结果。
11. 需要清理生成物时使用 `python3 scripts/clean-test-artifacts.py api` 或 `all`。

## 接口准入

可以进入自动化的优先级：

1. 只读查询接口。
2. 登录、鉴权、token 刷新等基础链路。
3. 报表、列表、详情、配置查询。
4. 可控测试数据下的创建/提交类接口。

默认不自动执行：

- 支付回调。
- KYC 提交、审核通过、审核拒绝（除非由专用测试数据和受控 runner 明确启用）。
- 后台配置修改、删除、开关切换。
- 奖励领取、签到、补签。
- 任何生产环境写操作，或未被专用 runner 明确覆盖的资金、审核、会员状态和配置变更接口。

P0 已批准的受控主流程写操作是例外：测试环境中的注册、充值下单/补单、提现申请及该专用提现单的后台同意和成功标记。执行条件、账号分层和当前覆盖状态只维护在 `api/p0/README.md`、`api/runbooks/API.md` 与 `AI-HANDOFF.md`，不在本 Skill 重复维护。
