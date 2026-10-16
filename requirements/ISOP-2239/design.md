# ISOP-2239：VCAT问题调整测试设计

当前结论：Jira正文已经明确四类调整，登录限制参数、密码接口差异、员工字段清理清单及安全响应标头不再作为泛化问题重问。本轮完成来源初扫和测试重点整理，尚未核对部署、执行业务请求或验证修复；全部测试为`NOT_RUN`。

[问题与决定](questions.md) · [测试重点与数据](test-cases.md) · [W27批次](../reviews/2026W27-20261016.md)

## 已确认规则

| 验收点 | 规则 | 来源 |
| --- | --- | --- |
| AC-01 | `/member/login`、`/member/v2/login`共用密码验证及同账号计数；30秒内第3次、3分钟内第6次请求触发10分钟限制。后端直接请求也生效，受限时停止继续验证密码，页面显示`Too many login attempts. Please try again in 10 minutes.` | Jira §001 |
| AC-02 | 手机验证修改／找回的`POST /member/retrieve/password`与邮件找回的`POST /member/retrieve/passwordbyemail`，验证身份后新旧密码相同须返回错误，不再返回成功。旧密码修改`POST /member/password/update`保留已有拒绝规则，只对齐新密码框的错误位置。首次设置沿用原流程；保持8～20位且至少含字母和数字及两次一致检查 | Jira §002“登录密码” |
| AC-03 | `POST /finance/wallet/pwd/update`的`old_pwd`／`pwd`及兼容入口`POST /member/wallet/password/update`的`old_password`／`new_password`均须在验证当前密码后拒绝新旧相同，不写入、不发送成功通知；资金密码保持六位数字和两次一致检查 | Jira §002“资金密码” |
| AC-04 | 手机、邮件、旧密码修改的失败停留相应输入页，在新密码框下显示现有登录密码英文错误提示。资金密码框标红并显示固定文案`New wallet password must be different from your current wallet password.`，不进入成功页。兼容资金接口不新增页面 | Jira §002“需要调整的情境” |
| AC-05 | 下表九个会员端读取接口，从列表、巢状对象和缓存响应中移除内部员工Email／账号及指定字段；后台审计、会员本人资料、公开客服资料保留 | Jira §003 |
| AC-06 | H5首页、直达页面、错误页的实际HTML响应统一安全标头；SPA须检查启动文档，不能只验JSON。避免CDN／代理／Web多层重复冲突，API和静态资源按适用规则覆盖 | Jira §004配置位置 |
| AC-07 | CSP先用Report-Only盘点真实来源，再切正式`Content-Security-Policy`阻挡；只保留Report-Only不算修复。内联脚本采用随机nonce或hash，不全面放开`*`、`unsafe-inline`、`unsafe-eval`；按实际需要分别配置资源、API／WSS、Worker、表单和第三方iframe来源 | Jira §004.1 |
| AC-08 | 一般H5页面使用`X-Frame-Options: SAMEORIGIN`及`frame-ancestors 'self'`；经确认可被第三方嵌入的页面仅按实际HTTPS origin放行并移除冲突的SAMEORIGIN。本站加载外部游戏用`frame-src`，不混淆两种方向 | Jira §004.1—2 |
| AC-09 | HTML／JS／CSS／图片／JSON及错误响应加`nosniff`并返回正确Content-Type；缺失JS／CSS不得被SPA fallback伪装成HTML脚本。H5使用`strict-origin-when-cross-origin`，删除覆盖它的宽松配置 | Jira §004.3—4 |
| AC-10 | Permissions-Policy按实际功能和来源授权；跨源KYC摄像头须header及iframe allow同时授权。示例来源须替换，不直接复制或用`*`全面授权，不误关正常KYC所需能力 | Jira §004.5 |
| AC-11 | HTTPS和证书核查后以HSTS一年为目标，可先短期验证；HTTP以301／308转到同主机HTTPS，仅HTTPS响应发HSTS。确认相关子域全部支持HTTPS后才加`includeSubDomains`，不直接加`preload`；测试和正式站分别核对 | Jira §004.6 |

### 员工字段清理范围

| 接口 | 正文要求移除的范围 |
| --- | --- |
| `GET /promo/task/newbie/list` | 任务及巢状资料的`created_name`、`updated_name` |
| `GET /member/game/listRw` | 游戏的`updated_name`及存在的`created_name` |
| `GET /promo/task/daily/list` | 每日任务及巢状资料的`created_name`、`updated_name` |
| `GET /promo/vip/config` | VIP配置的`updated_name`及存在的`created_name` |
| `GET /member/v2/index` | 首页聚合、nav、游戏及其他巢状对象的`created_name`、`updated_name` |
| `GET /member/vip/rule` | 规则列表和巢状资料中的上述字段及其他内部人员字段 |
| `GET /promo/turntable/detail?pid=16` | 转盘配置、奖项和详情中的上述字段及其他内部人员字段；其他pid同规则 |
| `GET /member/message/popup_list` | 消息及巢状资料中的上述字段及其他内部人员字段 |
| `GET /member/kyc/detail` | 上述字段及内部审核人员Email／账号，保留会员本人KYC资料和状态 |

## 影响与测试边界

- Jira优先级为“高”；建议先排账号限制、密码拒绝和员工资料泄漏，再完成正式CSP及第三方功能兼容验证。此为测试安排建议，不改Jira优先级。
- 后端验限制、接口拒绝及无副作用，人工UI验错误位置／停留页，浏览器与部署配置共同验实际响应头和正常业务兼容。成功返回、页面不报错、Report-Only存在均不足以判修复。
- 身份验证和不同新密码的正向恢复必须单独记录；错误密码、未通过手机／邮件验证不能绕过原身份校验。执行前须确定专用账号及恢复方式，本次扫描不修改密码、不进行高频请求或安全扫描。
- [已有业务规则](../../skills/business-rules.md)中的业务拒绝与无副作用方法可复用；当前资料不足以宣称已接入任何自动执行器、App验证或P0门禁。
- 登录窗口的边界／解禁时钟、错误契约、部署来源表及App适用面见[问题](questions.md)。只阻塞对应断言，不阻塞明确规则的准备。

## 来源与读取范围

实际读取日期：2026-10-16。主单[Jira ISOP-2239](https://alibaba-international.atlassian.net/browse/ISOP-2239)更新时间为2026-10-16 14:08:15.200（UTC+8），状态“待办”仅为工作流登记，不推导实现状态。

| 来源 | 已读范围与边界 |
| --- | --- |
| 主单正文§001—004 | 已读全文。正文关于“本机代码已确认”的结论属于来源陈述，本次没有复核业务源码、线上部署或入口防护 |
| 评论17515 | 共1条，分页范围完整；仅为附件访问说明，不含额外验收决定。访问口令不进入文档或提交 |
| [ISOP-2258后端](https://alibaba-international.atlassian.net/browse/ISOP-2258)、[ISOP-2259前端](https://alibaba-international.atlassian.net/browse/ISOP-2259)、[ISOP-2260 App](https://alibaba-international.atlassian.net/browse/ISOP-2260)、[ISOP-2261 QA](https://alibaba-international.atlassian.net/browse/ISOP-2261) | 4项已读，2026-10-16 14:06:38.088—14:06:45.044（UTC+8）更新；正文、评论均为空，均待办 |
| 附件 | 1份VAPT PDF（24306）与7张图（24304、24292—24295、24305、24303）只核到附件清单，未读取PDF及图片像素。正文称图2为本机代码绘制示意，不能作为线上截图 |
| 其他关联 | 返回的工作项链接及remote links为空；未发现正文外链文档，不据此排除未挂接资料 |

本次浏览器图片补读因连接中断未完成。保留附件待读范围，不宣称已完整复核原VAPT报告；测试重点及问题仅基于已读正文和子项。
