# ISOP-2110：編輯彈窗檢查邏輯調整

[设计](design.md) · [问题与决定](questions.md) · [测试用例](test-cases.md) · [总用例](cases.csv) · [来源同步](evidence-sync.md)

当前阶段：需求评审与用例设计；本轮未执行业务。规则完整性以[问题清单](questions.md)为准，接口契约/部署/账号样本尚未核定。

## 需求与验收依据

- 范围：KYC编辑提示触发时机；本次仅保留回归设计，沿用EKYC暂略过与已验收单不再测的用户决定。
- 主来源：[Jira ISOP-2110](https://alibaba-international.atlassian.net/browse/ISOP-2110)。
- 已有决定：不把当前提示条件修正扩大成编辑/复核权限重设计，既有用户留言可编辑及正式资料保护规则仍由2027维护。
- 关联：[ISOP-2027](../history/through-ISOP-2072/ISOP-2027/design.md)、[KYC长期规则](../../skills/business-rules/kyc.md)
- 环境：提测环境与版本待核；不从工单状态推定部署。

2026-09-18依据本会话已读取来源整理；本次落地未重新刷新远端。J正文/0评论及[E-KYC](https://alibaba-international.atlassian.net/wiki/spaces/bZaHTt6TIllW/pages/293928974/E-KYC) §7.2已核，图片/Confluence评论未核。

详细来源读取边界见[本日评审](../review-after-2072-20260918.md)。Jira状态仅为日期快照，不是本轮执行结果。

## 验收规则与待补项

明确规则标“明确”；待确认的AC只是设计槽位，不是可以执行的断言。来源简称J指本单Jira；来源范围逐行记录。

| 验收编号 | 性质 | 验收主题 | 来源／决定 | 用例 |
| --- | --- | --- | --- | --- |
| AC-01 | 明确；本轮略过 | 有signature且结果未返回 | J正文；E-KYC §7.2 | ISOP-2110-C01 |
| AC-02 | 明确；本轮略过 | 已有PASS/FAIL结果 | J正文；E-KYC §7.2 | ISOP-2110-C02 |
| AC-03 | 明确；本轮略过 | 无signatureID | J正文；E-KYC §7.2 | ISOP-2110-C03 |

具体步骤和断言维护在[test-cases.md](test-cases.md)，问题答复维护在[questions.md](questions.md)，避免重复维护公式。

## 影响与回归选择

KYC编辑提示触发时机；本次仅保留回归设计，沿用EKYC暂略过与已验收单不再测的用户决定。 身份、时间、金额或类型映射必须由独立样本佐证；旧结果不能代替本次验证。查询与计算优先API和只读对账；页面、布局、真实客户端行为由人工UI提供证据。

- 角色/数据前置按逐条用例准备，权限未定义时先明确，不凭原型账号推断。
- 新需求专项，不自动加入P0；P0具体Case映射待接口与改动范围确认。
- 遵循[业务规则](../../skills/business-rules.md)：数据库只读、资金链失败停止。配置保存需独立样本和恢复快照，游戏/资金/通知派发不在此次文档任务执行。

## 接口能力与可测性

本单以人工UI为主；暂无明确新增API要求，不为凑接口数量编造路径。关联调用若有变化再补契约对照。

尚无自动执行实现、plan.json或API参数矩阵；因此不生成api/data-cases.csv、不宣称一键可执行。固定回归与FAT/UAT实测证据均未交付。
