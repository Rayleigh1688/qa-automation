# ISOP-2027 阶段1、2实施记录

2026-09-11。依据[已批准计划](new-requirement-automation-plan.md)。本文记录阶段交付；2026-09-11随后按用户授权删除旧批次及归并报告，保留实施说明和日期结论，详见[清理记录](project-cleanup-2026-09-11.md)。当前不再有可导入的旧API原始证据。

后续用户已要求分离业务总表和数据驱动表：当前cases.csv从test-cases.md生成，API组合从plan.json生成api/data-cases.csv；下方阶段实施时的展开CSV行为已由[当前流程](testing-workflow.md)替代，执行ID和原始报告协议不改。

## 阶段1：统一用例与结果

已建立 `requirements/ISOP-2027/plan.json` 为新入口唯一执行源：保留原68条审阅编号，加入6条既有查询组合；CSV由源生成，历史编号不重排。未迁移场景明确NOT_RUN，不以历史PASS代替本轮执行。旧 `api/cases.json` 同样由plan.json生成；原查询CLI读取统一源构造兼容视图，原路径及产物不变。

`qa_core/execution_plan.py`提供数据集展开、类型保留的变量替换、顺序提取、接口/账号引用及断言校验；`qa_core/plan_runner.py`提供步骤结果、依赖停止与独立用例继续。缺字段与null、大整数与布尔类型分别处理。公共原始结果记录预期、脱敏实际、失败步骤、耗时和证据。配置继续使用既有环境加载器，actor B引用本地忽略的reviewer配置。

离线入口：`python3 scripts/run-requirement.py ISOP-2027`；`--export-cases`重新生成审阅CSV；`--only <id...>`与`--layer API`选择执行范围。`--rebuild <run目录>`仅从冻结原始结果及用例快照生成新的视图目录，不登录，不移动最近实测入口。完整执行命令在阶段2验收后记录。

验证：`npm run check`通过（247项单元测试）；首次沙箱内执行被既有测试的本机端口绑定权限阻止，经自动审核放行后重跑通过。当时的OFFLINE SAMPLE未更新latest，样例现已删除。阶段1没有业务登录。

## 阶段2：API完整可执行

已交付独立API入口，完成核心闭环、边界、鉴权、权限及两请求并发的固定资产迁移。CSV保留原编号，并自动展示执行步骤、断言和展开参数集。新增同类请求/参数反例只修改plan.json，不需要改执行器；复杂业务限定为注册/KYC准备、快照/对账、权限恢复和两请求竞争方法。

```bash
npm run qa:requirement -- ISOP-2027 --export-cases
npm run qa:requirement -- ISOP-2027 --env .env.fat --execute --insecure --allow-write kyc-review --allow-write kyc-permissions
```

`--only`选定编号、`--layer`按API/UI/FLOW筛选；跨账号核准/驳回为FLOW类型但属于本阶段API验收。默认仅离线校验，授权写范围与所选步骤不匹配时在登录前拒绝。测试授权沿用本次会话，BUG仍需另行确认，测试过程不发群。

### 实现与证据

- A/B/客户端使用显式会话，复用现有CBOR与TOTP；支持JSON、CBOR、multipart、请求头、正反例、类型保留的变量提取和结构/集合/前后状态断言。禁止跨域重定向和自动重试写请求。接口由契约资产注册，不放开任意URL。
- 每个独立写用例预留新号码，再核对注册手机号、UID、初始KYC状态。注册前预留状态写入忽略的`api/local-state/requirement-reservations-fat.json`，避免后台索引延迟导致重复分配。原P0号码游标语义保持；公共号码查询仅增加对明确`d=null,t=0`空页的兼容。
- ControlledFlow只用于串行注册/初次KYC准备，作用域结束后恢复原环境。正式请求不临时切换全局token。通用并发调度未开放；两请求竞争由固定方法先验证本轮归属、一次性提交两个已审请求，再只读核对。
- 写入前记录INTENT，业务ID/附件对象引用保存在0600本机检查点；公共报告不保存token或原始个人资料。失败停止依赖写步骤，只读诊断仍可取证，独立用例继续。结果逐步骤持久化，保留用例源快照与hash；不向结果目录生成session.py。
- 权限测试先核实B独占当前Codex角色，保存本轮原配置；finally恢复并fresh登录核对，recovery独立记录。恢复成功不改原FAIL，恢复失败可见并阻止后续业务请求。
- 新产物只写到`reports/qa/ISOP-2027/<run-id>/`。latest.html/latest.json指向最近真实执行（可为定向复验），离线归并/重建不更新它。旧P0/npm/查询CLI产物契约保留；已退出的历史报告已清理。

阶段2曾在2026-09-11 FAT验证主读写、边界、权限恢复、并发、查询及状态3/5组合；原批次标识为20260911T040816Z-c3787853、20260911T041944Z-a6f06bb3、20260911T042406Z-2432ecb0、20260911T042758Z-44802c76。旧结果现已删除，只保留这段日期来源说明；不能据此作为当前回归或BUG提交的原始证据。权限GET契约405的修正依据见[契约核对](../requirements/ISOP-2027/api/contract-review.md)。

### 剩余事项

- 后续已完成固定UI及团队执行包，并清理旧产物；当前以[团队分工](team-testing.md)为准。Telegram统一入口和自动留存未实施，P0资金链未随本阶段重跑。
- 状态1/4的准备契约、精确原因最大长度、第三个独立复核身份及故障注入仍不具备；相应用例NOT_RUN。500/1000/2000字节已独立观察，但不能据此推断最大值或计作最大值验收PASS。
- 原2027-API-022作为恢复索引保留NOT_RUN，实际恢复结果在019/020/021的recovery中，不伪造独立业务PASS。
- 批量详情返回额外记录、查询空集合null等仍作为契约观察/FAIL保留；后续写入仅使用本轮唯一UID，不操作额外记录。业务异常现场未操作；原始文件已清理，标识索引留在本机api/local-state，BUG提交前需补当前证据并确认。
- 本轮仅验收FAT/macOS；UAT、Windows/Linux实机及整个Story验收不由本次框架交付推定完成。

## 阶段验证边界

阶段2交付时`npm run check`通过258项离线测试，`git diff --check`通过。覆盖变量/断言、ID/null类型、HTTP200业务失败、空集合、编码与上传、会话隔离、不重放写入、依赖停止、只读诊断、号码预留、恢复失败和两请求竞争。曾与业务运行争用本机锁，待其释放后重跑通过，没有删除锁或绕过互斥。

以上是阶段交付时的检查，不是本次清理后新FAT验收。旧归并报告和调试轮次已删除；当前检查结果统一见[清理记录](project-cleanup-2026-09-11.md)。未完成的业务前提、UAT、Windows/Linux及整个Story验收不能据此推定通过。
