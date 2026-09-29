# ISOP-2091：开测评估与既有Bug核对（2026-09-29）

[设计](design.md) · [问题](questions.md) · [用例](test-cases.md) · [接口评审](api/contract-review.md)

## 结论

可以开始FAT测试。用户本轮明确版本问题先不管、接口以FB文档为准；部署版本号不作为开测门槛。当前6个直属子任务ISOP-2153—2158均为FAT测试，替代09-24“仅H5部分提测”的旧快照。父单仍为开发中，不据此阻塞测试，也不把子任务状态当作验收通过。

本轮完成来源、契约和去重核对，未登录业务系统或执行榜单/资金链测试。现有9条用例均未执行；可以先做只读配置、榜单、历史、报表与账变核对。造数、配置切换及调度重跑仍须具备隔离样本和明确操作入口，缺口按测试点记录，不泛化为整单阻塞。

## 既有Bug去重基线

本次检索得到17张直接相关Bug：待办1、已解决1、已完成15。状态是09-29读取Jira的快照，不代表本轮复测结果。

| Bug | Jira状态 | 已有问题范围 | 后续归属 |
| --- | --- | --- | --- |
| [TEST-3207](https://alibaba-international.atlassian.net/browse/TEST-3207) | 已完成 | 用户昵称数据需要脱敏 | C08：昵称脱敏 |
| [TEST-3205](https://alibaba-international.atlassian.net/browse/TEST-3205) | 待办 | 免费旋转没有生成对应的流水限制 | C05：Free Spin赢额→流水；沿用原单补证/回归 |
| [TEST-3193](https://alibaba-international.atlassian.net/browse/TEST-3193) | 已解决 | 厂商排行榜礼金备注错误，写成投注返利的备注 | C05：钱包账变类型/备注；优先回归原单 |
| [TEST-3192](https://alibaba-international.atlassian.net/browse/TEST-3192) | 已完成 | 历史数据查询没有代入查询时间 | C08：沿用原单定向回归 |
| [TEST-3191](https://alibaba-international.atlassian.net/browse/TEST-3191) | 已完成 | 历史数据与接口返回数据不一致 | C08：沿用原单定向回归 |
| [TEST-3190](https://alibaba-international.atlassian.net/browse/TEST-3190) | 已完成 | 游戏排行榜需要铺满10条 | C08：沿用原单定向回归 |
| [TEST-3189](https://alibaba-international.atlassian.net/browse/TEST-3189) | 已完成 | 游戏须知，需要铺满10条 | C08：沿用原单定向回归 |
| [TEST-3188](https://alibaba-international.atlassian.net/browse/TEST-3188) | 已完成 | 奖励前缀与设计稿不一致 | C08：沿用原单定向回归 |
| [TEST-3187](https://alibaba-international.atlassian.net/browse/TEST-3187) | 已完成 | 历史数据没有显示，清除假数据 | C08：沿用原单定向回归 |
| [TEST-3185](https://alibaba-international.atlassian.net/browse/TEST-3185) | 已完成 | 历史数据返回为空 | C08：沿用原单定向回归 |
| [TEST-3184](https://alibaba-international.atlassian.net/browse/TEST-3184) | 已完成 | 历史数据查询，不查今日 | C08：沿用原单定向回归 |
| [TEST-3183](https://alibaba-international.atlassian.net/browse/TEST-3183) | 已完成 | 自己在榜的时候，显示you | C08：沿用原单定向回归 |
| [TEST-3181](https://alibaba-international.atlassian.net/browse/TEST-3181) | 已完成 | 在没有投注的厂商下，也需要显示you | C08：沿用原单定向回归 |
| [TEST-3174](https://alibaba-international.atlassian.net/browse/TEST-3174) | 已完成 | 没有显示排行榜上其他用户的数据 | C08：沿用原单定向回归 |
| [TEST-3173](https://alibaba-international.atlassian.net/browse/TEST-3173) | 已完成 | 没有显示排行榜上其他用户的数据 | C08：沿用原单定向回归 |
| [TEST-3171](https://alibaba-international.atlassian.net/browse/TEST-3171) | 已完成 | 已经选择过的游戏不能重复选择 | C02/C07：排除游戏不可重复选择 |
| [TEST-3170](https://alibaba-international.atlassian.net/browse/TEST-3170) | 已完成 | 免费旋转派发应该可以多选 | C05/C07：Free Spin多选配置；需对照附件确认多选对象 |

优先处理TEST-3205和TEST-3193；其余15张作为已关闭问题回归基线。发现同一端、同一触发条件和同一结果时记录原Bug复现，不重新建单。跨端问题先核对原单覆盖范围；不同根因或独立业务结果才整理新候选。本轮不建单、不改Jira状态、不发消息。

本次未发现明确覆盖同分先达排序、结算时间跨日、配置次日生效不回溯、最后一天派奖、调度重跑幂等的独立Bug。这些是优先补测缺口，不是已确认缺陷。

## 开测顺序

| 顺序 | 范围 | 证据要求及去重方式 |
| --- | --- | --- |
| 1 | C01/C08：配置、前台详情/历史、后台报表 | fresh登录后确认实际活动39，按厂商/统计日/会员比对；关联3185/3187/3191/3192及3207，不把有响应当金额正确 |
| 2 | C05：奖励→钱包/商城币/Free Spin→流水 | 先取现有派发记录，现金=奖金×倍数、FS=赢额×倍数、商城币无流水；TEST-3205保留原单，3193检查账变备注 |
| 3 | C02/C04：排除、门槛、同分、多厂商 | 注单按结算时间独立重算；无同分/边界样本则只标对应点待样本，不推断通过 |
| 4 | C06/C09：跨日、配置生效、最后一天、幂等/通知 | 观察历史或新排程记录；无任务ID/重跑入口不能用多次查询冒充重跑；失败不发已到账通知 |
| 5 | C03/C07/C08：后台配置、导出、各端展示 | 配置隔离和恢复快照齐备后执行；导出需取到文件核内容；已有UI缺陷逐单回归，不重新进行整轮同题提单 |

## 来源与边界

- Jira主单：本轮重读正文、空评论、子任务列表；主单更新时间2026-09-23。正文规则未见推翻现有Q-01—Q-03。
- 6个直属子任务：正文、状态和评论均已读；2157共9条评论，其他5单0条。2157评论17451/17453确认09-25接入前台detail/list；17454仍描述本机mock对稿、未发布。仅保留为交付历史，不冒充真实业务通过。
- JQL两轮检索：父子任务及链接；TEST中“排行榜/2091”；跨项目“厂商排行榜/廠商排行榜/platform/rankings/venue/rankings”及QA子任务链接。两轮均返回isLast=true。另检出旧老虎机排行榜Bug，未混入本需求17张。语义搜索504后已由JQL完成替代。
- 17张Bug的标题、描述、状态、评论已读，均无评论；多数描述为截图，本轮未逐一查看图片，截图内细节和精确复现参数尚未全量核对。新候选与原单有疑似重合时，先补看附件再决定。
- [Lark需求](https://qsgpn7a1512s.sg.larksuite.com/wiki/KgnywLVttitU5YkIw4xlYNvzglb)本轮读取正文及可见1条评论，页面显示09-14更新。旧文“可上传Logo、可选派发时间”与Jira“沿用厂商Logo、固定04:30”不同，继续采用Jira明确细化规则；嵌入Board、Figma及原型未逐图验收。
- FB文档本地干净，HEAD与只读ls-remote得到的origin/main一致，均为c3cf68d560c6d6c2100dd5705923680e6aeed51f。文档版本不等于业务部署版本。
- 本轮机器证据检查仍UNREVIEWED；未伪造完整hash基线、业务PASS或自动执行实现。


## 本地验证

`npm run qa:cases -- ISOP-2091`生成9条用例；`npm run check:docs`通过243份文档；`git diff --check`通过。未运行全套单测或联网业务门禁，保留用户原有2092等未提交修改。
