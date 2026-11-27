# ISOP-2233：Pagcor责任博彩调整设计

[Jira事项](https://alibaba-international.atlassian.net/browse/ISOP-2233) · [问题与决定](questions.md) · [测试用例](test-cases.md) · [采集快照](../reviews/2026-11-23-ISOP-2233.md)

状态：需求评审 / 后端与H5准备；Jira页面状态为待办，Sprint为`ISOP面板 2026W28 11/26`。本文件依据2026-11-23只读采集形成，不代表提测、部署或功能已通过。

## 范围与来源

- 依据PAGCOR备忘录RGD-ADV26001（2026-11-11，附件）调整Filbet H5责任博彩（RG）内容。
- Jira要求2026-12-09前上线。
- 范围为Filbet H5登录前与登录后的所有页面、弹窗和宣传图；不另行证明App是否同步调整。
- 官方素材包括PAGCOR Logo、Responsible Gaming Logo（21+）和NPGH Logo，只能使用PAGCOR RGD发送的原文件，不可重制、裁切、旋转、改色或变形。

## 固定链接

| 名称 | 显示文字 | 链接 | 使用要求 |
| --- | --- | --- | --- |
| 自我排除入口 | `Online Self-Exclusion Application Portal` | https://osea.pagcor.ph | 新标签页直接打开，不经过中间页或跳转 |
| NPGH求助专线 | `NPGH Logo`或`NPGH.PH` | https://www.npgh.ph | 新标签页直接打开；Logo可作为链接 |
| 在线博彩客服表单 | `Online Gaming Platform Helpdesk` | https://forms.cloud.microsoft/r/fGpVFA00Gf | 新标签页直接打开，不经过中间页或跳转 |

## 明确规则

| 验收点 | 业务预期 | 来源 |
| --- | --- | --- |
| AC-01 | 全站页脚位于每页底部，且完整显示在导航栏、浮动按钮、弹窗或Banner上方。登录前、登录后页面均适用。 | Jira正文§1 |
| AC-02 | ABOUT显示Terms of Use、Privacy Policy，并链接到现有页面；CONTACT US固定Filbet客服邮箱与电话，不放PAGCOR邮箱；下载/社交入口沿用现有入口。 | Jira正文§1 |
| AC-03 | 页脚并排显示PAGCOR、Responsible Gaming、NPGH三个Logo；点击NPGH跳转npgh.ph；每个Logo高度至少40px，手机宽度不足时排成两行。 | Jira正文§1 |
| AC-04 | 页脚显示固定求助文案、电话、NPGH链接、自我排除入口、Helpdesk年龄限制、公司牌照和Copyright © 2026 FilBet ALL RIGHTS RESERVED。 | Jira正文§1 |
| AC-05 | 宣传图底部左右满版增加20%白条；横式依据Figure 1、竖式依据Figure 2排列，不重新排列元素。横幅素材放在右侧。 | Jira正文§2/Annex A |
| AC-06 | 白条只能包含PAGCOR、Responsible Gaming、NPGH、指定求助文案、RGD联系邮箱、核准编号和ASC编号；核准编号字段依图片核准情况填写或留空。字体为Proxima Nova，不放活动文字或装饰。 | Jira正文§2 |
| AC-07 | 首页轮播、Promos、活动内页、首页弹窗、登录/注册窗口顶部宣传图等指定位置一律完整显示，不裁切、不拉伸；显示比例跟随图片比例。 | Jira正文§2 |
| AC-08 | 首页弹窗广告对同一会员24小时内最多显示3次；未登录时按设备计算。 | Jira正文§2 |
| AC-09 | 进站RG确认弹窗更新自我排除文案/链接、增加RGD与Helpdesk内容、将NPGH文案改为链接，并按规则显示三个Logo。 | Jira正文§3 |
| AC-10 | Notice弹窗和My页底部Logo列沿用进站弹窗规则；Responsible Gaming页新增指定Need help区块；Terms of use页更新联系和排除/求助链接。 | Jira正文§4 |
| AC-11 | 顶部App下载文案改为`Get the Filbet App`；全站不得出现指定的“now”类文案或不区分大小写的变体。 | Jira正文§5 |
| AC-12 | NDRP名单中的会员登录时拒绝登录，并显示固定锁头弹窗、文案、客服邮箱/电话/渠道及OK按钮；点击OK保持未登录。其他封锁原因沿用原提示。 | Jira正文§6 |

## 待确认及阻塞

- 页脚是否同时出现在游戏全屏页、存款和提款弹窗，需向RGD询问。
- 外部Filbet客服电话、邮箱和客服渠道名称。
- 三个现有页面是否保留PAGCOR邮箱；备忘录只明确禁止页脚使用PAGCOR邮箱。
- 白条Need Help文案以长文还是示例图为准。
- 宣传图白条的新尺寸比例及手机可读性。
- 首页弹窗上限是否同时适用于轮播和Promos Banner。
- NDRP判断方式：实时查询PAGCOR还是沿用封锁状态。
- App是否同步调整。
- 17:00—20:00不得新上架宣传内容，由后台限制还是运营人工控制。

未取得相应答复前，相关用例保持BLOCKED，不将现有实现或页面文案当作新预期。

## 来源与读取范围

| 来源 | 读取结果 |
| --- | --- |
| [Jira ISOP-2233](https://alibaba-international.atlassian.net/browse/ISOP-2233) | 2026-11-23已读取页面正文、附件清单和侧栏；状态待办、优先级高、Sprint为W28、报告人Darren、经办人未分配、评论区未见新评论。 |
| PAGCOR RGD-ADV26001 | 附件清单已取得：`PAGCOR RGD-ADV26001 advertising memo 2026-11-11.docx`；本轮未下载或逐页核对附件。Jira正文将备忘录规则转述为验收依据。 |
| Annex A/B/C | 附件名称和尺寸已读取：横/竖宣传图、页脚、NDRP弹窗；本轮未下载像素核对，视觉尺寸、色彩和版面仍需实际核验。 |
| 旧合规文件 | 已看到附加的`Filbet RG 合规检查 from devdeMac-mini.html`，未读取内容，不能作为本次PAGCOR最新口径。 |

未读取子任务、历史评论、linked work、附件内容和远端部署；未执行页面、API、数据库、NDRP或业务登录操作。
