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

1. 先读 `api/runbooks/API.md`。如果处理后台接口，再读 `api/runbooks/ADMIN.md`。
2. 接口文档只负责发现接口，不能直接决定用例价值。新增接口必须先映射到 `api/p0/main-flow-scenarios.csv` 的业务场景。
3. P0 统一管理在 `api/p0/`：
   - 用例：`api/p0/test-cases.csv`
   - 场景：`api/p0/main-flow-scenarios.csv`
   - 报告：`api/p0/smoke-report.md`、`api/p0/write-smoke-report.md`
   - 只包含 API 资产；UI 报告和结果必须放在 `ui/reports/`、`ui/results/`。
4. 每条用例不能只看 HTTP 200，至少要断言：
   - 响应可解码。
   - 业务 `status=true`。
   - `data` 类型符合预期。
   - 关键字段存在。
5. FAT 当前使用 CBOR 请求/响应，runner 执行时使用 `--body-format cbor`。
6. FAT 当前本机证书链需要临时 `--insecure`，只允许用于测试环境。
7. 真实账号、OTP、Google code、token、cookie、设备 id 只能通过环境变量或 CI secret 注入，不写入仓库。
8. `api/results/*.json` 是最近一次 API 原始执行结果，每次覆盖刷新，不做历史累计，且不提交。
9. `api/p0/*.md` 是 API Markdown 结论，每次覆盖刷新，可提交作为当前状态。

## 接口准入

可以进入自动化的优先级：

1. 只读查询接口。
2. 登录、鉴权、token 刷新等基础链路。
3. 报表、列表、详情、配置查询。
4. 可控测试数据下的创建/提交类接口。

默认不自动执行：

- 充值下单、提现申请、支付回调。
- KYC 提交、审核通过、审核拒绝。
- 后台配置修改、删除、开关切换。
- 奖励领取、签到、补签。
- 任何会改变资金、审核状态、会员状态或生产配置的接口。

## 当前基线

- P0 只读 smoke：30 条，客户端 25 条 + 后台 5 条。
- P0 主流程写操作：注册通过、充值订单创建通过、提现申请未调通。
- 已知老接口：
  - `/member/game/list` 不作为通过标准，优先使用 `/member/v2/index`、`/member/game/listRw`、`/member/game/list/recommend`。
  - `/member/vip` 不作为通过标准，优先使用 `/promo/vip/config`、`/promo/vip/sign/in/config`。
