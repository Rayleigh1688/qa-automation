# P0 API AI Runbook

## 目标

这套资产用于让任意 AI 代理或自动化执行器在不依赖对话上下文的情况下，完成 P0 客户端 API 冒烟验证。

当前覆盖范围是客户端核心只读链路：

- 登录：短信 OTP 发送、OTP 登录。
- 财务：渠道、充值记录、提现 tab、账变、钱包、提现记录。
- 游戏：游戏记录、历史游戏、最近游戏、推荐游戏、新版游戏组合、新版首页聚合。
- KYC：会员 KYC 详情。
- 会员/VIP：会员详情、VIP 等级详情、新版 VIP 配置、新版 VIP 签到配置。

## 资产入口

| 文件 | 用途 |
| --- | --- |
| `api/interface-inventory.csv` | Bruno 全量接口资产清单，包含原始 URL、清洗 URL、标记、P0 候选 |
| `api/interface-inventory.md` | 接口资产摘要 |
| `api/p0-interface-shortlist.csv` | P0 候选接口清单 |
| `api/p0-interface-shortlist.md` | P0 候选摘要 |
| `api/p0-main-flow-scenarios.csv` | P0 主流程正反例场景矩阵 |
| `api/p0-main-flow-scenarios.md` | P0 主流程正反例说明，给功能测试和 AI 共用 |
| `api/p0-test-cases.csv` | P0 可执行测试用例，runner 直接读取 |
| `api/p0-test-cases.md` | P0 测试用例说明 |
| `api/p0-smoke-report.md` | 最近一次人工整理后的 smoke 结论 |
| `scripts/api-smoke-runner.py` | 登录、请求、CBOR 编解码、断言执行器 |
| `scripts/render-p0-smoke-report.py` | 将 JSON 执行结果渲染为 Markdown 报告 |

## 环境变量

不要把真实凭据提交到 Git。用本地 shell、`.env` 或 CI secret 注入：

```bash
API_URL=https://client-fat.filbet2025.com
CLIENT_PHONE=<client phone>
CLIENT_OTP=<otp code>
DEVICE=25
LANG_HEADER=en_US
```

后台登录已经验证可用，但当前 P0 可执行用例只跑客户端只读接口。后台只读 P0 后续单独建用例集。

## 执行命令

FAT 测试环境当前需要临时跳过本机 TLS 证书校验：

```bash
CLIENT_PHONE=<client phone> CLIENT_OTP=<otp code> \
python3 scripts/api-smoke-runner.py \
  --cases api/p0-test-cases.csv \
  --with-client-login \
  --limit 18 \
  --execute \
  --insecure \
  --body-format cbor \
  --out api/p0-smoke-result.json
```

生成 Markdown 报告：

```bash
python3 scripts/render-p0-smoke-report.py \
  --result api/p0-smoke-result.json \
  --cases api/p0-test-cases.csv \
  --out api/p0-smoke-report.md
```

## 通过标准

每条用例至少满足：

- HTTP 状态为 `200`。
- 响应可解码为 CBOR 或 JSON。
- 业务字段 `status=true`。
- `data` 类型符合用例要求。
- 关键字段存在，例如钱包接口必须包含 `uid`、`balance`、`withdrawable`、`locked`。

## 用例排序原则

`api/p0-test-cases.csv` 按玩家业务流程排序，方便 AI 和人类阅读：

1. 注册登录：由 runner 作为前置动作完成，不作为普通 CSV 用例。
2. KYC。
3. 充值。
4. 投注。
5. 派彩/投注相关数据检查。
6. 提现。
7. 以上相关数据检查。
8. 后台报表展示和审批。

底层执行器可以按依赖关系、登录态和安全策略调整实际请求顺序，但报告和用例资产以业务流程为主。

## 场景设计原则

`api/p0-main-flow-scenarios.csv` 是上层场景资产，用来沉淀主流程正反例。新增接口进入可执行 P0 前，先判断它属于哪个场景：

- 注册登录：OTP、token、三方登录、验证码规则、鉴权失败。
- KYC：查询、提交校验、重复提交、状态限制。
- 充值：渠道、下单、金额边界、通道不可用、记录检查。
- 投注：新版游戏列表、旧接口替代、非法参数、维护游戏。
- 派彩：投注记录、派彩记录、账变核对。
- 提现：提现配置、提现申请、余额/KYC/资金密码限制、记录检查。
- 相关数据检查：钱包、账变、会员、VIP、活动配置。
- 后台：报表展示、审批列表和详情、权限、审批动作跳过。

写接口自动化时，不能只根据接口文档生成用例。接口文档负责发现接口，主流程场景负责决定测试价值和正反例边界。

## 暂不自动执行

以下接口类型默认不自动执行：

- 充值、提现、回调。
- 创建、更新、删除。
- KYC 提交、审核、驳回。
- 领取奖励、签到、补签。
- 后台配置修改。
- 任何依赖真实资金、审核流、第三方回调或不可自动回滚的数据写操作。

## 已知替代关系

| 老接口 | 状态 | 替代接口 |
| --- | --- | --- |
| `GET /member/game/list` | HTTP 200 但业务 `status=false` | `GET /member/v2/index`、`GET /member/game/listRw`、`GET /member/game/list/recommend` |
| `GET /member/vip` | HTTP 200 但业务失败 | `GET /promo/vip/config`、`GET /promo/vip/sign/in/config` |

## 给 AI 的操作顺序

1. 先读本文件。
2. 再读 `api/p0-main-flow-scenarios.csv` 和 `api/p0-test-cases.csv`。
3. 确认环境变量存在，不要把凭据写入仓库。
4. 执行 runner。
5. 渲染报告。
6. 如果失败，优先看 `assertion_failures`，再看 `decoded_body`。
7. 不要自动执行 `manual_review` 或 `review_only` 接口。
