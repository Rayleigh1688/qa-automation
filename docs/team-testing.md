# API自动执行与UI人工验收

2026-09-11，按用户最新澄清：**P0继续维护API与核心UI自动化；新需求采用API自动执行、UI人工验收，暂不建设新需求UI自动化。** 此次调整只影响新需求的后续投入。旧P0、资金链及Telegram状态保持；旧报告已按用户授权清理，见[整理记录](project-cleanup-2026-09-11.md)。

## 自动化范围

| 范围 | 执行方式 | 后续工作 |
| --- | --- | --- |
| P0核心回归与已授权资金链 | API自动化 + 核心UI自动化 | 继续维护现有用例、定位和执行入口，真实页面及三方游戏交互仍由UI验证 |
| 新需求专项 | API自动执行 + UI人工执行 | AI整理用例、准备数据、分析结果；测试人员执行页面步骤并回填，不安排新增UI脚本或扩建UI框架 |

已有新需求UI脚本仅保留兼容能力，不列入当前实施计划；当前UI验收以人工证据为准。后续需求如需纳入P0，单独按P0准入评审，不在新需求阶段顺带建设UI自动化。

## 用例分工

用例仍按需求/模块/验收点组织，`类型`表示API/UI/FLOW验证层级；`delivery.mode`独立表示automatic/manual执行方式。API覆盖业务规则、参数矩阵、鉴权、状态、边界和精确数据对账；手动覆盖页面展示、交互、反馈、预览和代表性用户流程。相同业务场景可以有不同层级断言，但不把API参数组合再复制成人工点选矩阵。数据库只读。

[人工用例plan示例](../requirements/_template/team-plan.example.json)用于新增需求起步，须替换占位内容。`plan.json`仍是执行配置唯一维护源；业务总表维护在test-cases.md，文件分工见[用例与数据分离](testing-workflow.md#文件与执行入口)。人工执行项在plan中维护：人工项增加`delivery.precondition/steps/expected`中文说明；不要求添加Playwright步骤。已有自动步骤保留，自动结果不能自动升级为人工PASS。原用例ID、验收点和旧CSV字段不重排。

ISOP-2027新增`execution_policy=api-first`：新入口默认执行自动分配项，包含API型和后台FLOW；仍受既有写范围门禁约束。`--only`、`--layer UI`显式选择或`--include-ui-automation`可使用原UI自动化。其他未设置策略的需求保持原行为。未实现的人工项即使误选自动入口，也只记NOT_RUN。

## 一次交付

```bash
# 离线生成执行包；目录必须是新的，不登录
npm run qa:delivery -- prepare ISOP-2027 --environment FAT --out reports/qa/ISOP-2027/team-next
# API/后台自动执行；没有--execute时只校验
npm run qa:requirement -- ISOP-2027 --execute --insecure --allow-write kyc-review --allow-write kyc-permissions
# 人填好manual.csv后，导入到新目录；可选一份或多份真实自动结果
npm run qa:delivery -- import --packet reports/qa/ISOP-2027/team-next --manual reports/qa/ISOP-2027/team-next/manual.csv --out reports/qa/ISOP-2027/team-next-reviewed
```

执行时可用`--version <发布标识>`记录声明版本，与准备包的`--version`一致；它不代表实际核验部署。无版本仍记“未提供”。团队包支持按统一计划选择的子集，也可仅含API；仅API时manual.csv只有表头。

导入命令可重复提供`--auto-results <实测目录/result.json>`。必须保留该来源的plan.snapshot.json。不会按时间偷偷挑PASS：同一用例提供两个自动来源时拒绝，需先明确选取哪份证据。允许不同批次的明确证据汇总，但报告醒目标注“本次导入未执行测试”，记录每个来源的run-id、时间和hash，不改最近实测指针。源环境必须相同，声明具体部署版本时也须一致；逐条比较实际执行步骤、参数/变量及观察标记，旧契约结果不能冒充新版本。来源中的人工分配项/未选项被排除并记录，不把旧UI脚本PASS算作人工完成。

执行包提供：

- `api-auto.csv`：自动执行侧审阅表，标明可执行或具体缺口。
- `manual.csv`：人工步骤和回填列；初始全部NOT_RUN。`samples/`提供256、512000、512001字节合成PNG，避免人工另外造边界文件；会员和待审申请仍需按本批授权准备。
- `results.html`：全范围准备视图，不表示执行通过。
- `packet.json`、plan/cases快照：固定本批身份、环境、版本和用例内容。

## 人工怎么回填

只改六列：**执行状态、实际结果、证据、执行人、执行时间、未执行原因**。不改编号、步骤、预期、环境、版本或批次。CSV可在Excel、WPS或文本编辑器编辑，以UTF-8 CSV保存，保留完整行和列。

| 状态 | 必填内容 |
| --- | --- |
| NOT_RUN | 未执行原因，例如“本批待审样本尚未准备”；不能把没测留白当通过 |
| PASS / FAIL / ERROR | 实际结果、证据、执行人、执行时间；清空未执行原因 |

时间使用带时区的ISO格式，例如`2026-09-11T15:00:00+08:00`，不能是未来。证据填写本地文件路径（相对manual.csv或绝对路径）或HTTPS引用；本地文件必须存在。工具校验填写结构及关联，不会验证截图内容真实性或替代测试人员判断。截图和说明先脱敏，不填写账号密码、token、证件或个人原始资料。HTTPS引用只记录，不自动联网核查。

导入拒绝缺行/重复编号、改动固定列、未知状态、缺执行信息、失效本地证据或不匹配的自动来源。有效回填复制到新的报告目录并计算hash；原CSV、原结果及失败现场均不覆盖。结果CSV/HTML区分执行方式、执行人、执行时间和来源批次。没有自动证据的自动项也保持NOT_RUN。

## 本轮交付与边界

试点交付：[API自动表](../reports/qa/ISOP-2027/team-ready-20260911/api-auto.csv) · [UI人工清单/回填表](../reports/qa/ISOP-2027/team-ready-20260911/manual.csv) · [准备视图](../reports/qa/ISOP-2027/team-ready-20260911/results.html)。自动侧71条（65条有执行步骤，6条尚缺前提/实现），人工18条，既有编号保留。

旧导入演示、离线样例与阶段归并报告已删除。当前准备视图仍全部NOT_RUN，没有实际人工回填；最近实测另从`reports/qa/ISOP-2027/latest.html`查看，不能把它当作本批人工结果。旧API原始来源已清理，需执行新批次后再导入。

新需求执行、执行包准备及导入默认只生成`results.csv`/`results.html`两份结果视图；HTML内可搜索和筛选失败/未执行。需要额外`cases.csv`、`failures.csv`、`pending.csv`、`summary.json`时，对相应命令加`--extra-views`。原始result.json、冻结快照、api-auto.csv、manual.csv和必要证据仍保留。旧P0、查询CLI及通用qa:report产物契约不变。

最新离线验证见[整理记录](project-cleanup-2026-09-11.md)。本次没有执行FAT API/UI或实际人工验收；BUG提交仍需确认，测试过程不发群。

下一步由团队使用UI清单真实执行并回填，继续完善API数据、断言和执行效率。新需求UI自动化不列为后续待办；P0的API和核心UI自动化继续维护。Telegram已接入统一API结果、按范围生成团队包和import-manual回填，见[提测流程](telegram-qa.md)。旧执行包和活动任务未迁移；自动留存仍待后续，Jira投递规则保持。
