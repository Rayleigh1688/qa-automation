# ISOP-2375 VACT 接口测试

默认访问 FAT 客户端域名 `https://client-fat.filbet2025.com`。请求和机器断言见 [test-cases.json](test-cases.json)，分页及场馆参数见 [datasets.yaml](datasets.yaml)。[plan.json](../plan.json) 引用这些文件，并选择匿名、普通会员及钱包测试会员会话。

## 执行

从仓库根目录运行。

```bash
npm run qa:api -- ISOP-2375 --execute
```

普通会员使用 `.env.fat` 中的 `CLIENT_PHONE`、`CLIENT_PASSWORD`。钱包用例使用已有的 `WITHDRAW_CLIENT_PHONE`、`WITHDRAW_CLIENT_PASSWORD`。先校验配置时省略 `--execute`。也可用虚拟环境中的 `python scripts/run-requirement.py ISOP-2375 --fat-api --execute`。 [短命令和适用范围](../../../docs/commands.md#fat-只读-api-短命令)

本计划准备了 13 条只读接口用例。每条发一次目标请求并独立判定。其他品牌、分支、广告、转盘、无游戏样本的会员推荐和三方登录场景保留在 [验收审阅稿](test-cases.review.json)。

单独复跑两条 VIP 员工字段检查：

```bash
npm run qa:api -- ISOP-2375 --execute \
  --only ISOP-2375-C23-RESP ISOP-2375-C26-RESP
```

## 查看报告

命令结束后输出本批 `reports/qa/ISOP-2375/<批次>/results.html`。本机直跑时，展开用例可查看步骤请求、HTTP 和业务状态、完整解码响应正文及每条断言的预期、实际和判定。CSV 记录实际判定的 PASS／FAIL，脱敏步骤证据和运行诊断保存于同批 `result.json`。 [API 测试报告模板](../../../docs/testing-workflow.md#api-测试报告模板)

C28 的 `trigger_person`、`maintainer` 须缺失、为 `null` 或为空字符串。字段检查失败时，先看响应正文上方的完整统计，再对照实际返回的字段和值。

本轮报告生成后，旧的同环境纯 API 结果视图在输出新报告路径前清理。各批的结果 JSON 和冻结快照留作复查及重建。 [报告清理与重建](../../../docs/commands.md#报告精简与清理)
