# ISOP-2375：VACT 驗證調整功能与接口测试用例

[设计与验收依据](design.md) · [问题与决定](questions.md) · [Jira事项](https://alibaba-international.atlassian.net/browse/ISOP-2375)

依据2026-11-27 Jira正文验收项目（A01–A08）建立初评用例。全部未执行；实际测试前需先确认FAT部署状态及Q-01—Q-05待确认项。

<!-- case-cards:v1 -->
## 用例总览

| 编号 | 用例名称 | 状态 | 负责人 |
| --- | --- | --- | --- |
| ISOP-2375-C01 | [无token调用11支公开API敏感字段清理校验（A01）](#c01) | BLOCKED | ukr |
| ISOP-2375-C02 | [带会员token调用3支需登录API敏感字段清理校验（A02）](#c02) | BLOCKED | ukr |
| ISOP-2375-C03 | [站内信列表接口隐藏发送人与维护人字段（A03）](#c03) | BLOCKED | ukr |
| ISOP-2375-C04 | [站内信弹窗接口维持不返回后台人员字段（A04）](#c04) | BLOCKED | ukr |
| ISOP-2375-C05 | [会员详情钱包密码字段清空与日志脱敏（A05）](#c05) | BLOCKED | ukr |
| ISOP-2375-C06 | [会员详情三方登录授权字段清空与展示（A06）](#c06) | BLOCKED | ukr |
| ISOP-2375-C07 | [后台管理端员工操作人字段正常显示回归（A07）](#c07) | BLOCKED | ukr |
| ISOP-2375-C08 | [会员端相关页面功能与展示回归（A08）](#c08) | BLOCKED | ukr |

## 用例详情

<a id="c01"></a>
### ISOP-2375-C01：无token调用11支公开API敏感字段清理校验（A01）

**前置条件：** 确认FAT已部署`release`最新修复版本（Q-03）；准备无登录态请求环境。

**操作步骤：**
1. 不带Authorization/token依次请求第1–5、7、8、10–12、14项共11支API：`/promo/list`、`/promo/task/newbie/daily`、`/promo/task/daily/task`、`/member/game/list/recommended`、`/member/buriedPoint/detailV2`、`/member/v2/index`（覆盖filgame、filslots、filplay、karakrus版本）、`/member/game/listRw`、`/promo/turntable/detail`、`/promo/task/newbie/list`、`/promo/task/daily/list`、`/member/vip/rule`。
2. 逐一检查完整JSON/CBOR响应体（含嵌套`list`、`nav`、`Daily`、`rets`等结构）。

**预期结果：** 所有响应中均不存在`created_name`、`updated_name`、`operator_name`、`created_uid`、`updated_uid`、`operator_uid`字段，或对应字段为空值，且原有业务数据正常返回。

**待确认：** [Q-02](questions.md#q-02)、[Q-03](questions.md#q-03)。

<a id="c02"></a>
### ISOP-2375-C02：带会员token调用3支需登录API敏感字段清理校验（A02）

**前置条件：** 确认FAT已部署修复版本；准备已登录普通会员账号与有效token。

**操作步骤：**
1. 携带会员token依次调用第6、9、13项API：`/finance/payment/bank/list`、`/member/game/list/recommend`、`/promo/vip/config`。
2. 检查响应体所有层级字段。

**预期结果：** 响应中均不存在`created_name`、`updated_name`、`operator_name`、`created_uid`、`updated_uid`、`operator_uid`字段，或对应字段为空值；银行列表、推荐游戏及VIP配置业务字段完整。

**待确认：** [Q-02](questions.md#q-02)、[Q-03](questions.md#q-03)。

<a id="c03"></a>
### ISOP-2375-C03：站内信列表接口隐藏发送人与维护人字段（A03）

**前置条件：** 确认FAT已部署修复版本；准备后台操作账号与测试会员账号；确认`total_send_count`、`read_count`、`target_users`是否一并移除（Q-01）。

**操作步骤：**
1. 在管理后台向测试会员发送一条站内信。
2. 使用测试会员token调用`/member/message/list`。
3. 检查返回消息列表中的每条记录字段。

**预期结果：** 响应中不存在`trigger_person`、`maintainer`字段或为空值；若Q-01确认移除统计/目标字段，则`total_send_count`、`read_count`、`target_users`亦不返回。

**待确认：** [Q-01](questions.md#q-01)、[Q-03](questions.md#q-03)。

<a id="c04"></a>
### ISOP-2375-C04：站内信弹窗接口维持不返回后台人员字段（A04）

**前置条件：** 准备存在弹窗站内信的测试会员账号与token。

**操作步骤：**
1. 使用测试会员token调用`/member/message/popup_list`。
2. 检查返回体字段。

**预期结果：** 维持现有行为，响应中不存在`trigger_person`、`maintainer`字段或为空值，弹窗内容正常返回。

**待确认：** [Q-03](questions.md#q-03)。

<a id="c05"></a>
### ISOP-2375-C05：会员详情钱包密码字段清空与日志脱敏（A05）

**前置条件：** 确认FAT已合入`10cbcd5`及日志清理改动；准备已设置6位钱包密码的测试会员账号；具备FAT后端日志查看权限。

**操作步骤：**
1. 使用该会员token调用`/member/detail`。
2. 检查响应体`member_extra.wallet_password`及`has_wallet_password`字段。
3. 查询调用时刻对应后端服务日志，检索`WalletPassword`或bcrypt哈希特征字符串。

**预期结果：** 响应中`wallet_password`为空、`has_wallet_password`为`true`；后端日志中不输出钱包密码明文或bcrypt哈希。

**待确认：** [Q-03](questions.md#q-03)、[Q-04](questions.md#q-04)。

<a id="c06"></a>
### ISOP-2375-C06：会员详情三方登录授权字段清空与展示（A06）

**前置条件：** 准备使用三方账号（OAuth）登录的测试会员账号。

**操作步骤：**
1. 使用三方账号登录并获取会员token，调用`/member/detail`。
2. 检查`oauth_secrets`、`ThirdPartyTy`、`ThirdPartyName`等字段。

**预期结果：** `oauth_secrets`为空（或未返回），`ThirdPartyTy`与`ThirdPartyName`正常显示。

**待确认：** [Q-03](questions.md#q-03)、[Q-04](questions.md#q-04)。

<a id="c07"></a>
### ISOP-2375-C07：后台管理端员工操作人字段正常显示回归（A07）

**前置条件：** 准备管理后台有效账号及权限；FAT已部署修复版本。

**操作步骤：**
1. 登录管理后台，依次进入活动列表、任务设定、游戏列表、银行列表、埋点设定、转盘活动、站内信列表页面。
2. 核对列表及详情中创建人、修改人、操作人字段显示及对应管理接口返回。

**预期结果：** 后台各模块创建人、修改人、操作人字段均正常显示，未受会员端字段清理（特别是共用model或结构体调整）影响。

**待确认：** [Q-02](questions.md#q-02)、[Q-03](questions.md#q-03)。

<a id="c08"></a>
### ISOP-2375-C08：会员端相关页面功能与展示回归（A08）

**前置条件：** 准备FAT会员端（H5/Web）测试环境与测试会员账号。

**操作步骤：**
1. 在未登录与已登录状态下依次访问会员端首页、活动页、签到、任务、VIP、转盘、充值/银行选择、站内信及个人中心/钱包密码相关页面。
2. 检查页面渲染、接口报错及核心交互操作（领取/跳转/银行选择/查看站内信等）。

**预期结果：** 上述页面展示正常，交互操作无报错或字段缺失异常。

**待确认：** [Q-03](questions.md#q-03)。
