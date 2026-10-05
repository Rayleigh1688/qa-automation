# 客户端代理申请与邀请码链路：10-02实测

[前批开户记录](verification-20261002-priority.md) · [2100投注后对账](verification-20261002-post-bet.md)

**最新决定：2026-10-02用户会议确认交互流程没问题，工作转回2100数据及特殊样本。** 不再将自行取得邀请码的入口观察或A_client待审核作为2100数据测试的阻塞，也不继续要求用户审批。该决定不等于补做了以下未执行步骤；申请、审批和页面的原始事实保留。

此前实测：申请可提交，已成为代理的页面未展示代理邀请码或邀请链接。本轮使用独立申请号A_client和已开通代理A_kyc分开核验；后台查询邀请码及API注册不冒充客户端自助通过。时间均为2026-10-02、GMT+8。

## 客户端提交申请：通过

- A_client为本仓库已创建的独立FAT测试会员，申请前KYC5、正常普通会员、无代理设置、直属0、历史申请0；未改变2100三名资金样本。
- UI密码登录成功。真实路径为`/my` → “Apply To Become An Affiliate” → `/s-affiliate` → “Apply To Become An Affiliate” → `/s-affiliate/apply`。
- 表单Email、FB Messenger Username必填，四问题Optional；填写专用测试资料、四问题留空。用户分别明确同意通用Terms／Privacy和本次独立代理协议及提交后，勾选协议并提交一次。
- 页面显示“Your Application Has Been Submitted”和“Under Review”；14:52:25.762新建申请，数据库必填资料与本次UI一致。14:43:59打开表单后仍0条的旧快照保留，不能继续写成尚未提交。
- 当前协议`/s-affiliate/terms` §1.1明确Full KYC，§2说明代理专属推荐链接。当前页面已有KYC要求文字依据，但不据此外推完整后台资格公式。

证据：[提交成功页面](../../reports/qa/ISOP-2100/20261002-client-closure/ui/application-submitted-under-review.jpg)、[提交后只读核验](../../reports/qa/ISOP-2100/20261002-client-closure/preflight/post-submit.md)、[代理协议](../../reports/qa/ISOP-2100/20261002-client-closure/ui/affiliate-terms.txt)。准确账号、申请ID和合成测试资料留忽略目录。

## 本次申请审批：验证码阻塞

用户另行明确授权批准本次测试申请，最初自动审批审查指出的授权范围不足已解除。独立代理管理后台可登录，审核列表返回本次精确UID和申请ID；使用现有通用管理员审批TOTP执行一次批准，HTTP200但`status=false`、`invalid verification code`。14:59:04.619只读复核仍state1、audit_uid0、updated_at0、代理设置0行，未授予代理资格。

原失败证据保留，未使用固定登录验证码代替审批码，未直接转代理绕过失败。通用TOTP的既有验证范围为主管理后台，不足以证明独立代理管理后台绑定相同。用户先表示手动批准；15:11:57.308只读复核仍待审。之后用户明确指出对应验证器为本机忽略文件agency-admin-QR.png，离线确认其SHA256／6位／30秒、密钥与主管理不同，未修改任何绑定或将密钥写入配置。

已准备改用该验证器仅重试同一精确申请，保留首个业务失败；执行前自动审批审查因“此前用户决定手动批准”拒绝，命令未启动、没有发出第二次业务审批。已再次请求明确改由助手操作；当前等待该授权范围冲突解除。新的验证器尚未证明当前业务审批成功。

审批页面位置已实查为独立代理管理后台“代理管理 → 代理审核”，路径`/agent/agent-review`；该后台与主管理后台的直接开通是不同操作。

另：审核详情请求以`uid`查询时Email／FB返回空，而精确申请列表及DB资料存在。详情参数／当前UI调用尚未核实，作为未完成观察保留，不能直接判资料丢失。

证据：[批准请求记录](../../reports/qa/ISOP-2100/20261002-client-closure/admin-approve/events.json)、[失败后副作用核验](../../reports/qa/ISOP-2100/20261002-client-closure/preflight/post-approval-failure.md)。

## 已批准代理自行获取邀请码：未闭环

用前批已开通的A_kyc独立检查：

| 位置 | 当前实际 |
| --- | --- |
| 客户端My | 入口仍显示“Apply To Become An Affiliate” |
| 客户端`/s-affiliate` | 显示“Congratulations! You Are Now An Affiliate Of Filbet.”，底部只有“Contact customer service”；无邀请码、邀请链接、复制或代理后台跳转入口 |
| 代理后台首页／账号菜单／Account Settings | 首页为统计；账号菜单仅改密码、退出；Account Settings仅改密码；未展示邀请码 |
| 代理后台Rates | 佣金阶梯／税率／厂商费率，未展示邀请码；未修改配置 |
| 代理管理后台 | 前批精确代理记录已有非空`invite_code`，三名下线用该值通过客户端API注册且直属关系正确 |

当前客户端已知`/member/detail`没有`invite_code`，`referral_code`为空，普通好友`shared_code`与后台代理邀请码不同；`/agency/profile`只返回统计。不能把普通好友邀请参数`i`当作代理`invite_code`，也不能拼接未验证的代理分享链接。

结论限于实测页面与当前契约：**邀请码后台已存在且API绑定有效，代理本人在已检查的客户端成功页和代理后台入口无法自行取得。** 不宣称所有潜在入口都不存在，亦未将联系客服视为自助闭环或实际发送消息。

证据：[已成为代理但无邀请码页面](../../reports/qa/ISOP-2100/20261002-client-closure/ui/approved-agent-affiliate-no-invite.jpg)、[页面文字](../../reports/qa/ISOP-2100/20261002-client-closure/ui/approved-agent-affiliate-no-invite.txt)、[My入口](../../reports/qa/ISOP-2100/20261002-client-closure/ui/approved-agent-my.txt)、[代理后台账号菜单](../../reports/qa/ISOP-2100/20261002-client-closure/ui/existing-agent-account-menu.txt)、[Rates](../../reports/qa/ISOP-2100/20261002-client-closure/ui/existing-agent-rates.txt)、[前批代理记录](../../reports/qa/ISOP-2100/20261002-priority/account/agency-record.json)。

## 历史未验证边界

最后核验时申请未审核通过；新用户通过当前UI输入代理邀请码、注册后直属归属未完成。前批三名会员证明API链路有效，不替代这些UI环节。以上为实测边界；按页首最新会议结论，本轮不再将补齐邀请码展示／复制入口或继续此申请审批列为2100前置条件。

旧13:22 `POST /member/agency/apply`的404保留，但实际UI已提交并写入申请，不能用旧请求断言当前客户端申请失败。本轮未捕获提交请求路由，不把历史FB契约写成当前页面实际调用；本地FB `59946fe`相对`2b7ecef`相关申请契约未变，未据此推断部署版本。

本轮业务写入为用户批准的客户端申请与一次失败审批；没有数据库写入、追加充值／投注、配置变更、外部提单或消息。截图、原始API/SQL、凭据和准确身份均留本机忽略目录；独立代理菜单发现不撤回2100已有页面／金额失败。
