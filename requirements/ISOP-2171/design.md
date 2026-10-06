# ISOP-2171：FILPLAY用户端界面调整测试设计

[设计](design.md) · [问题](questions.md) · [测试重点](test-cases.md) · [W26评审](../reviews/2026W26-20261006.md)

Phone登录、背景预留及提示方向已明确；指定Figma节点部分未读，浏览器Pop-ups语义为补证推断，完整交互决定在[问题文档](questions.md)维护。来源读取日期为2026-10-06。本次仅按最终W26评审迁移到任务单目录，未刷新远端来源、未重新测试；已确认规则、待确认决定及历史交付陈述分开记录。

## 已明确方向

- 正文要求保留Phone登录方式，背景预留后续替换空间。
- Pagcor及Pop-ups要求“每次进入弹窗提示”，目前不将这句话自行解释为某一生命周期事件。
- 页面入口精简不自动要求禁用全部服务端登录协议或账号迁移；背景预留不自动新增后台换图系统。

## 设计读取与推断

[Figma指定节点1466-23679](https://www.figma.com/design/5Y2Qpf6qxGWBwAIwkkqxDY/260428_FilPlay_Redesign?node-id=1466-23679)本轮未能定位，加载落回Thumbnail；文件可访问，不能断言节点已删除或完整稿缺失。指定稿布局、批注及平台条件仍部分未读，设计证据为PARTIAL。

跨页搜索可见`Enable Pop-ups For Better Experience`、Safari允许弹出窗口及关闭Block Pop-ups文案，因此**Pop-ups优先指浏览器设置引导**；这是语义补证推断，不作为本单最终平台条件，也不解释成营销／奖励弹窗。搜索结果不替代指定稿完整读取，其他页面的Phone注释没有移植为本单决定。

## 执行边界

当前仅有初步测试重点；未冻结像素、完整Phone流程或提示计次断言。取得有效设计定位与规则后，按H5／App当前构建分别验收，不以跨页搜索代替完整设计评审。

## 规则决定入口

- [Q-01：Phone设计与登录范围](questions.md#q-01)。
- [Q-02：每次进入的计次事件](questions.md#q-02)。
- [Q-03：两提示条件与顺序](questions.md#q-03)。
- [Q-04：背景替换交付范围](questions.md#q-04)。

## 来源

| 来源 | 定位与读取范围 |
| --- | --- |
| Jira正文 | [ISOP-2171](https://alibaba-international.atlassian.net/browse/ISOP-2171)，Phone、背景及两类提示；读取2026-10-06 |
| Figma | [指定节点](https://www.figma.com/design/5Y2Qpf6qxGWBwAIwkkqxDY/260428_FilPlay_Redesign?node-id=1466-23679)，文件可访问、原节点未定位；跨页搜索仅补证Pop-ups语义，读取2026-10-06 |
| 最终评审 | [W26 FILPLAY评审](../reviews/2026W26-20261006.md#isop-2171filplay用户端界面调整)，本次迁移依据 |
