# ISOP-2027 阶段3：UI完整可执行

2026-09-11，依据[已批准计划](new-requirement-automation-plan.md)，接续[阶段1、2](new-requirement-stage1-2.md)。本轮使用既有FAT测试授权；BUG未提交，测试过程未发群，当时的原修改和异常现场未覆盖。后续已清理旧报告与调试轮次，当前仅保留本文最后一批真实UI证据，见[清理记录](project-cleanup-2026-09-11.md)。

后续用户已调整为[API自动优先、UI人工验收](team-testing.md)：本文保留阶段3交付时的行为与证据；当前新需求UI由人工执行，既有UI脚本仅保留兼容，不列为后续建设项；P0的API与核心UI自动化继续维护。

## 实现

- `requirements/ISOP-2027/plan.json`继续作为唯一执行源，UI步骤与API/业务方法共享actor、变量、提取、断言和四状态结果。生成CSV保留原UI/FLOW编号。普通动作与用例只修改JSON；正式运行不扫描页面，不调用AI，不导入结果目录脚本。
- [固定页面资产](../ui/data/isop2027.json)使用服务别名和页面路径，集中维护列表、表单、确认框、复核抽屉、图片预览等定位。旧`isop2027-fat.json`已确认无当前消费者并删除。目标必须唯一；文档槽位使用明确位置，并先断言集合大小为3或6，不能静默取首项。
- `ui/framework/requirement-ui.mjs`提供可导入的打开、真实点击、输入、选择、勾选、上传、等待、键盘、滚动及观测能力。表单先等待本轮原值初始化；响应监听在触发前安装，同时关联新request对象和本轮参数。HTTP与业务状态分别断言；前端拦截检查有界窗口内请求数为0，并检查页面反馈与适用的API不变性。
- `scripts/telegram-ui.mjs`成为兼容CLI，旧scan/run实现迁到可导入的`legacy-requirement-ui.mjs`，原命令、scan/result文件和状态口径保留。Telegram接入统一新入口属于后续阶段5，未在本轮替换。
- `filbet/requirement_ui.py`通过`qa_core/json_worker.py`驱动常驻Node浏览器worker，凭据通过私有stdin传递，不进入命令参数/报告。每轮每actor建立fresh UI会话，本轮用例间打开页面重置，独立会员不共用。浏览器认证后的token只在内存中同步给同actor API会话，并核对真实身份；后续对账不额外登录踢掉UI。
- 浏览器请求白名单与当前步骤写门禁同时生效：scope、当前用例UID/申请ID、正在触发的契约必须相符，写请求放行前持久化INTENT，每步最多放行一次写请求。不重试写入，不强制点击，不修改DOM绕过遮挡。策略拦截、定位/解码/响应缺失属于ERROR；明确断言不符和已确认真实点击遮挡属于FAIL。
- 新产物仍只写入`reports/qa/ISOP-2027/<run-id>/`，保存plan、页面资产快照/hash、步骤耗时、脱敏结果、私有写检查点和必要失败证据。新运行使用独立目录；最近实测指针不由离线重建更新，历史留存按当前清理约定处理。

## 使用

```bash
# 离线校验并更新审阅CSV，不登录
npm run qa:requirement -- ISOP-2027 --export-cases
# 固定UI用例（未具备权限前提的用例仍列NOT_RUN）
npm run qa:requirement -- ISOP-2027 --layer UI --execute --insecure --allow-write kyc-review
# 两条双账号三图UI流程：API准备 → B页面编辑 → A页面复核 → API对账
npm run qa:requirement -- ISOP-2027 --only 2027-FLOW-003 2027-FLOW-004 --execute --insecure --allow-write kyc-review
```

当前省略`--only/--layer`时按api-first策略只执行自动分配项；包含UI的完整自动范围须显式加`--include-ui-automation`。`--layer API`只选API类型，阶段2的FLOW-001/002需用`--only`明确选择。新UI试点仅覆盖FAT后台，不使用旧资金profile，不改变P0资金入口。

## 实测过程与证据

最终整批：`20260911T050501Z-d626392b`。[结果树](../reports/qa/ISOP-2027/20260911T050501Z-d626392b/results.html) · [结果CSV](../reports/qa/ISOP-2027/20260911T050501Z-d626392b/results.csv)。18条：**15 PASS、1 FAIL、2 NOT_RUN、0 ERROR**。这是同一轮新会员实测，不是历史归并。

- PASS覆盖只读字段、无变更、空原因、图片上下边界、精确已处理UID/申请ID筛选、只读详情、六张前后图片预览，以及B三图编辑→A核准/驳回→三端资料与审计对账。
- FAIL仅UI-014 Restore：真实点击被旁边Replace photo按钮遮挡；[局部截图](../reports/qa/ISOP-2027/20260911T050501Z-d626392b/2027-UI-014-restore-click-target.png)与`ui-diagnostics.jsonl`保存命中元素/矩形证据。未强制点击，依赖的还原后提交未执行。属于待确认候选，不自动建BUG。
- NOT_RUN为UI-015/016权限矩阵，原批次记为“尚未迁移”，本轮plan已进一步明确具体角色/契约缺口，未撤改角色配置。
- 记录耗时：准备53.755秒（含API登录0.865秒）、显式API请求9.279秒、UI63.709秒（含本轮UI登录和15秒遮挡等待）、对账13.892秒、报告3毫秒。各项不是纯产品响应时间；本批UI登录尚合并在首次页面步骤中。

前序白名单/表单时序排障批次和中间结果已在2026-09-11清理。相应脚本问题已修正，不作为产品BUG；当前证据以最后整批为准。

## 验证和边界

`npm run check`最终通过（261项单元测试、110份文档），`git diff --check`通过；本地浏览器验证18条结果、FAIL/NOT_RUN筛选和编号搜索通过。包含worker超时退出与重复关闭检查、原P0与Telegram CLI兼容；本轮FAT不重跑旧P0资金链。新增本地真实浏览器验证了请求关联、旧响应排除、HTTP200业务拒绝、multipart上传、无请求窗口、严格定位、遮挡取证和actor隔离；离线校验拒绝未知页面/元素/动作、缺绑定、无断言及缺HTTP/业务断言的响应步骤。

本轮未实施完整权限UI矩阵（UI-015/016缺角色/新复核权限契约）、第三复核人竞争、故障注入与统一中断恢复验收。用户后续已转向API自动、UI人工，暂停通用混合流程扩建；团队模板、按需视图及本次历史清理已交付。Telegram统一接入及自动留存未实施，状态库未改。只在macOS/FAT验证，不推定UAT、Windows/Linux实机通过，也不将阶段3框架交付等同整个Story验收通过。
