# ISOP-2031：用戶端 - 新增金額動畫效果 — 测试设计

当前阶段：需求评审/测试准备；不代表业务测试通过。复审日期：2026-09-08（UTC+8）。

[可分派测试用例](test-cases.md) · [问题与决定](questions.md) · [批次评审](../review-summary.md) · [需求索引](../README.md)

## 来源与范围

- [Jira正文](https://alibaba-international.atlassian.net/browse/ISOP-2031)；创建：2026-09-03T18:38:52.747+0800；读取时最后更新：2026-09-07T22:55:42.498+0800；Story状态：待办（仅来源快照）。
- 子任务：[ISOP-2080](https://alibaba-international.atlassian.net/browse/ISOP-2080)、[ISOP-2081](https://alibaba-international.atlassian.net/browse/ISOP-2081)、[ISOP-2082](https://alibaba-international.atlassian.net/browse/ISOP-2082)、[ISOP-2083](https://alibaba-international.atlassian.net/browse/ISOP-2083)；本轮已读取，正文/评论无补充。状态不代表部署或验收。
- 范围：到账提示弹窗、金额动画及通知消费；金额展示效果不能承担实际记账。
- 补充来源与关联：[Lark来源](https://qsgpn7a1512s.sg.larksuite.com/wiki/UU0Sw9J5GiSJBukGkR5l6hLWgDe)、[投注返利](../ISOP-2032/design.md)
- 读取边界：本轮已重读Jira、全部关联子任务及Lark。新增两张充值路径截图、动画ZIP；本轮未逐张核对截图、未播放视频或解包验证动画。

## 验收依据

下表整理来源中明确的规则；推荐的可靠性/权限场景在用例中标示为测试设计。有歧义的部分以问题编号关联，不把建议当成已批准需求。

| 验收编号 | 业务预期 |
| --- | --- |
| AC-01 | 从派发时间起1个月内有效；登录后在登录相关弹窗关闭后展示。不保证送达，单事件最多一次；通知到期不清除奖金。日历月定义及消费契约见Q-02。 |
| AC-02 | 本版三事件：充值成功、Daily Reward、投注返利。Daily Reward免费旋转提示后续Sprint。充值文案You have successfully Top Up!；Daily Reward为Congratulation! You received Daily Reward Bonus!；返利文案冲突见Q-01。 |
| AC-03 | 派发当下位于首页/Game/Rewards/Filcoin/My时即时展示动画通知；位于其他页面则等返回任意上述五页，只展示最终弹窗图片、不播放动画。Game列表不等于进入三方游戏。 |
| AC-04 | 首页充值和My充值两条路径均移除Details详情页，充值完成返回首页，收到成功通知后展示效果；返回触发点及先后竞争见Q-04。Transactions进度入口和Header金币图标按关联Lark回归。 |

## 本轮变更

三类事件及五页条件已明确；旧Lark额外事件不作为本版必测。API/MQTT由2080交付，重点验证共同事件ID和登录弹窗排队。返利聚合方式归2032 Q-07，不能把类型分账当成多个必须独立弹出的通知。

## 测试分工与准备

准备可复用的事件回放/测试时钟、在线与游戏中场景；不得靠真实重复充值制造通知。先核对事件契约再写去重断言。

目标环境先以 FAT 准备；各端实际部署版本、接口路径/参数、账号角色与受控执行范围需在提测单核实。需求或原型可访问不代表功能已经部署。方法标为API/只读对账的用例需要实际接口返回和独立数据期望；不凭UI展示一致推定后端计算正确。

只有需求阶段先确认规则、盘点样本、冻结契约并分派用例；后端提测后先验证契约/业务状态/金额和异常副作用；前端提测后执行交互与跨端联调；最后对受影响模块回归。本需求暂不自动加入P0，不新增或复制runner。执行步骤及证据统一进入 [用例文件](test-cases.md)，讨论只更新 [问题文件](questions.md)。
