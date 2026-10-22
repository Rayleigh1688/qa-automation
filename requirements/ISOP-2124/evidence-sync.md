# ISOP-2124：来源同步与用例交付

[设计](design.md) · [问题](questions.md) · [测试用例](test-cases.md) · [总表](cases.csv) · [XMind](ISOP-2124-测试用例.xmind)

2026-10-20已重新读取Jira主项、全部评论范围与三个子任务，并将正文明确规则编为63条正式卡片和XMind。当前为**PARTIAL**：Q-01审核中充值冲突、Q-02责任博彩触发行为未解决，图像与关联设计仍有未读范围。所有用例NOT_RUN；文档、CSV及导图生成不表示提测、部署或业务通过。

## 来源及本次读取

| 来源编号 | 定位与来源版本 | 实际读取日期与范围 |
| --- | --- | --- |
| J | [ISOP-2124](https://alibaba-international.atlassian.net/browse/ISOP-2124)，updated 2026-10-16 15:01:22.479（UTC+8） | 2026-10-20读取完整正文共用部分及§1—9，主项待办；与10-16采用规则无新决定。§4.2与§5.1冲突仍在，§4.4所指待确认清单仍未出现在正文末尾 |
| JC | 同一主项评论 | 2026-10-20返回0条、total 0、startAt 0，无待续页；未取得Q-01／Q-02答复 |
| CHILD | [2241 H5](https://alibaba-international.atlassian.net/browse/ISOP-2241)、[2242 App](https://alibaba-international.atlassian.net/browse/ISOP-2242)、[2243 QA](https://alibaba-international.atlassian.net/browse/ISOP-2243) | 2026-10-20以parent查询，3条且isLast=true。正文空、评论均0／total 0、附件与关联项为空。2241、2243待办；2242进行中、updated 2026-10-20 10:06:35.915（UTC+8）；不能据状态认定构建可测 |
| LINKS | 主项issuelinks及remote links | 2026-10-20两者均空；正文链接另行读取，不把空remote links当没有关联材料 |
| ATTACH-META | 主项30项附件元信息，PDF及原图／v2图片 | 2026-10-20重新取得元信息。文件名、数量和创建时间不等于已读取视觉内容，也不按v2文件名机械覆盖正文 |
| FIGMA | [指定节点](https://www.figma.com/design/5Y2Qpf6qxGWBwAIwkkqxDY/260428_FilPlay_Redesign?node-id=1599-15276) | 2026-10-20直接读取返回不可访问。仅保留10-16已看整体分组、部分评论及Bag局部的历史边界；没有补读逐屏内容 |
| ANIMATION | [动画目录](https://drive.google.com/drive/folders/1406NAVosGdphg8XiS6yGVXRmdyN1Ma2v) | 2026-10-20直接读取返回不可访问；未遍历或播放动画 |
| CLAUDE | [正文产物链接](https://claude.ai/artifact/Qt85akXxDtLzuESAMYjzu5) | 2026-10-20直接读取返回不可访问；未取得产物内容 |
| VISUAL | 主项`Filplay 子品牌架構設計.pdf`与附图 | 本次未视觉读取。10-16充值v2图片预览停加载也未读到像素；不将其计入已确认预期 |
| CROSS | [ISOP-2123设计前提](../ISOP-2123/design.md)及[主项](https://alibaba-international.atlassian.net/browse/ISOP-2123) | 2026-10-20定向重读前提及§1—3，updated仍2026-10-16 14:08:05.777（UTC+8），评论0／total 0。只采用共享UID／KYC、分站钱包／存提款／交易／游戏列表规则；不继承2123或历史需求执行结果 |

正文没有Lark链接，本次未虚构关联文档。Sprint信息沿用2026-10-16快照，本次没有重查Sprint；名称中的10/29不当作上线日期。已读与未读分开登记，不能以未访问成功断言原材料也没有答案。

## 影响映射

| 变更编号 | 来源 | 用例 | 同步与验证边界 |
| --- | --- | --- | --- |
| S01 | J、JC、CHILD、LINKS | C01—C22、C26—C29、C31—C60、C63 | 将原10组测试重点拆为具体前置、操作、预期与副作用检查；分别覆盖H5／App。状态全NOT_RUN，专用执行计划未实现 |
| S02 | J、JC、CHILD | C30 | 保留Q-01冲突；预期明确待确认，不选择允许或禁止作为PASS依据 |
| S03 | J、JC、CHILD | C23—C25 | 保留Q-02，拆时长、时段、输额三组；触发后的在玩／重进行为未冻结，不以设置保存通过替代 |
| S04 | CROSS、J | C61、C62 | 共享身份与钱包隔离写为跨需求检查，源记录逐站对照；不恢复旧2090业务任务 |
| S05 | FIGMA、ANIMATION、CLAUDE、VISUAL | 所有卡片涉及的视觉细节，重点C02、C08、C19、C45 | 仅正文明确流程已同步；布局、未读字段约束和动画补读后再增补，不能宣称全量设计验证完成 |
| S06 | J §5.3—5.4、本轮独立评审 | C36 | 补齐错误钱包密码和取消后的订单、可用／冻结余额、提款账变检查，明确不得建单、扣款／冻结或产生提款账变；成功提交仍按实际合同核对。仅完善失败副作用检查，未刷新来源或执行业务 |

当前`test-cases.md`是设计源，`cases.csv`通过既有`qa:cases`离线导出。XMind先用既有`qa:xmind export`生成，再用共享XMind模块将同一批用例按13个模块组织、步骤逐项显示；保留显式模块字段、全部九字段和待确认依赖。展示重组不更改业务定义，Markdown与XMind不要同时各改一份步骤。

## 本地验证

- 生成前已执行`npm run qa -- evidence ISOP-2124`，返回UNREVIEWED（退出码2），如实表示尚无机器基线；此次逐条对照来源、问题和卡片后登记部分基线。
- `npm run qa:cases -- ISOP-2124`成功：63条，API执行数据未实现；CSV状态均NOT_RUN，47条高、16条中。
- 既有`qa:xmind export`与`qa:xmind import`成功。最终导图导入后的63条×9字段与源CSV投影逐字段一致，编号唯一；4条待确认预期和依赖保留，向右布局声明有效。
- 导图有13个模块及独立评审说明，63条用例详情默认折叠。2026-10-20通过CUA在XMind客户端实际打开当时成品：画布加载、待确认标签可见；实际折叠全部模块，再展开“启动与登录”，读到C01—C04的前置、步骤和预期，随后两次Undo恢复折叠。当次未操作保存，打开前后导图SHA256与当时登记值一致；这不是63条逐条视觉验收。
- 2026-10-22提交前重新核验当前文件：字节已不同于10-20登记版本，包内新增缩略图、`content.xml`及Vana 26.03.04129创建者元数据，符合客户端重存格式；具体重写时间和操作者未证实。保留当前文件，更新机器记录`artifacts`中的交付SHA256；ZIP完整，经共享导入模块读取的63×9字段与CSV及正式卡片一致，13模块、4条待确认预期和依赖保留。本次没有重演客户端保存流程或重新做视觉验收，业务测试仍未执行。
- `npm run check:docs`通过（320个文件）；`qa evidence ISOP-2124 --allow-pending`通过且如实显示PARTIAL；本目录`git diff --check`通过。机器检查不证明远端持续无更新。
- 未执行API／UI业务、资金／KYC／派发／封锁操作，未修改Jira或发送外部消息；未创建自动执行计划。完整全项目检查由本轮整合统一记录，不能以离线检查替代业务结论。

最终文件的SHA256见机器记录`evidence-sync.json`的`artifacts`字段；该二进制hash是交付定位，正文基线检查仍只检查文本文件。日期、未读范围和待答问题发生变化时，需重新语义核对后更新基线，不能仅重算hash。
