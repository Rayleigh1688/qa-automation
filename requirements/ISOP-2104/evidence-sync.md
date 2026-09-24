# ISOP-2104：证据同步记录

[设计](design.md) · [问题与决定](questions.md) · [测试用例](test-cases.md) · [总用例](cases.csv) · [来源同步](evidence-sync.md)

## 来源基线

2026-09-18依据本会话已读取来源整理；本次落地未重新刷新远端。J正文及评论17347/17348/17349已读，5个直属子任务正文/评论空；Figma及附图未逐张核。2032正文/评论及用户决定作为计返依据。

详细来源读取边界见[本日评审](../review-after-2072-20260918.md)。Jira状态仅为日期快照，不是本轮执行结果。

[Jira ISOP-2104](https://alibaba-international.atlassian.net/browse/ISOP-2104)

## 本次落实

| 变更 | 来源与性质 | 落地位置 | 验证边界 |
| --- | --- | --- | --- |
| S01 | J§一/三及评论17349；2128评论17394/17403访客B版；Q-01核交付 | AC-01 / ISOP-2104-C01；design.md、questions.md、test-cases.md、生成cases.csv | 访客前置已明确；NOT_RUN，版本/契约未核，无业务执行 |
| S02 | J§一至四；2118§2及2128评论登录A版；Q-01核交付 | AC-02 / ISOP-2104-C02；design.md、questions.md、test-cases.md、生成cases.csv | 登录前置已明确；NOT_RUN，版本/契约未核，无业务执行 |
| S03 | J§四；2032 Q-02/Q-05；Q-02显示金额、Q-06结算阶段仍待产品决定 | AC-03 / ISOP-2104-C03；design.md、questions.md、test-cases.md、生成cases.csv | 页面展示口径BLOCKED，无业务执行 |
| S04 | J§四/六 | AC-04 / ISOP-2104-C04；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；NOT_RUN，无业务执行 |
| S05 | J§六 | AC-05 / ISOP-2104-C05；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；NOT_RUN，无业务执行 |
| S06 | J§二/五 | AC-06 / ISOP-2104-C06；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；NOT_RUN，无业务执行 |
| S07 | J§三/四；Q-03跳转、Q-05合计比例 | AC-07 / ISOP-2104-C07；design.md、questions.md、test-cases.md、生成cases.csv | 设计同步；BLOCKED，无业务执行 |
| S08 | J§六未决边界；Q-04无可展示游戏、Q-07不足10个、Q-08加载失败 | AC-08 / ISOP-2104-C08；design.md、questions.md、test-cases.md、生成cases.csv | 已有访客规则移至C01；其余BLOCKED，无业务执行 |
| S09 | 2032 Q-05及2026-09-16用户决定；已有门槛/封顶规则 | AC-09 / ISOP-2104-C09；design.md、questions.md、test-cases.md、生成cases.csv | 派发规则对账独立准备；NOT_RUN，无业务执行；不推定页面展示 |

## 2026-09-23问题分流

仅依据上述已读来源及仓库中2032、2118的既有记录重排问题，未刷新Jira/Figma或取得新答复。Q-01交付核验从产品决策中分出；Q-02至Q-04仍待答复，具体一次确认包见[问题文件](questions.md#一次确认包与并行工作)。C01/C02由业务预期BLOCKED改为版本待核的NOT_RUN，C09把已确认派发计算从C03页面展示断言中分离；均不是执行通过或部署确认。

同日后续重读[2118 Jira](https://alibaba-international.atlassian.net/browse/ISOP-2118)新增正文及2128开发评论：二期A版会员统计、访客B版已明确，2128称前端发SIT；Q-01已据此缩为前后端版本/契约/非零样本核验。未独立核SIT/Figma，未改变Q-02页面金额口径或本需求执行状态。

## 2026-09-23问题写法调整

按用户要求改为短标题索引和“场景→问题点→需要确认”，来源/用例关联后置。保留Q-01—Q-04，原Q-03的合计比例拆至Q-05，原Q-02的结算阶段拆至Q-06，原Q-04的数量不足/接口失败拆至Q-07/Q-08；问题变细不表示新增需求。已有访客B版依据从待答描述移到C01，C08继续保留推荐边界和加载失败；C09金额示例补明确“后两组满足门槛”的前置。

同步AC/Case问题引用，业务用例仍为9条、执行状态未变。更新问题模板和写法约定，其他需求未批量改写；此次仅沿用前述证据，未刷新远端或执行业务测试，机器基线仍未登记。

## 未完成

上述未读素材与待确认问题仍保留；未建立远端完整同步或自动执行就绪结论。本目录尚未登记机器hash基线，证据检查应显示UNREVIEWED，而不是伪造完整已审阅。收到新决定/补读来源后逐项更新再登记。

## 2026-09-24功能用例与API对账分开评审

将原宽表改为短名称索引和“前置条件、操作步骤、预期结果、待确认”卡片。功能文档保留C01—C08；原C09完整迁到[API与对账用例](api/test-cases.md#c09)，C03链接对应记录。上方S09的历史位置为迁移前的test-cases.md，当前以api/test-cases.md为准。

九条用例的编号、验收点、Q依赖、执行状态和负责人均保留；C09仍保留三组派发0、5、0以及“后两组满足返利门槛”的前置，不用派发金额替代页面预期。没有新增请求、接口参数或可执行数据驱动资产。

C03按已有Q-06补清Today未结算、Yesterday未派发及已派发的阶段记录/快照前置。C09的已结算记录仅供最终派发对账，缺少其他阶段证据时不能完成全部页面检查。

此次仅整理本地文档与存放位置，沿用前述2032/2104/2118证据；未刷新远端、补读设计素材、取得新业务决定或执行业务测试。机器证据基线仍未登记。
