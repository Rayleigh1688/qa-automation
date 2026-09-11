# ISOP-2027 FAT权限API验证（2026-09-10）

> 留存说明（2026-09-11）：本文是原日期的文字结论。用户已授权删除旧结果、扫描和临时脚本，文内旧路径只表示历史来源，不能作为当前可复核/可导入证据；当前入口与保留范围见[清理记录](../../../docs/project-cleanup-2026-09-11.md)。

用户将第二管理员改为Codex角色，并明确角色配置入口`/system/role`和权限字典`fat.fb_admin_priv`。本轮按新的Codex角色配置为恢复基线，未将B恢复到先前超级管理员角色。A保持原管理员权限。Codex当前成员查询仅B一人。

## 已完成的权限组合

| 操作 | 有权基线 | 撤权后fresh登录B | 恢复后 |
| --- | --- | --- | --- |
| POST /admin/kyc/list（20001） | 查询成功 | 返回拒绝 | 查询成功 |
| POST /admin/kyc/edit（20006） | 独立会员编辑成功，A正常驳回基线申请 | 返回拒绝，资料/申请/审计无变化 | 编辑成功，A正常驳回恢复验证申请 |
| GET /admin/kyc/ekyc/log（20007） | 查询成功 | 返回拒绝 | 查询成功 |

通过`/admin/group/update`仅移除三项权限，原始模块/按钮权限、名称、备注、父级、状态和排序均保存并核对恢复。恢复后B保持用户指定Codex角色。首次副作用快照因后台身份切换覆盖客户端token而中断，角色在finally中已恢复；后续fresh会员登录补齐快照并复验编辑，不重发撤权写请求，不隐藏首次脚本中断。

## 普通角色复核阻塞

- Codex已有全部现存KYC权限时，`GET /admin/kyc/review/list`即返回HTTP200、status=false、data=permission；A同条件返回status=true。
- 本轮A创建的独立待复核申请，由Codex角色B直接调用`POST /admin/kyc/review`也被拒绝，前后资料/申请/审计不变。
- 只读查`fat.fb_admin_priv`全部KYC/复核匹配项：有列表、初次KYC拒绝/通过、删除、编辑、异动记录及会员KYC详情；没有`/admin/kyc/review/list`、`/admin/kyc/review`或`/kyc-review`节点。`fat.fb_admin_button_priv`也无KYC/复核匹配节点。
- 结论：普通角色当前无法通过现有权限树获得新增复核能力，存在权限配置缺口候选。需要补齐正式权限节点/映射与分配后重验；不直接写库补节点掩盖问题，也不将角色改回超级管理员制造通过。
- 计划的“撤销整个KYC模块后测试复核拒绝”未开始，因为有权正例已失败；不能把该角色始终无法访问当成撤权检查通过。涉及正常B复核的UI闭环同样未完成。

## 其他观察与证据

账号列表文档标GET，实测405；实际POST查询可读取并核对角色成员。新会员的单UID批量KYC详情返回两行（仅一行UID匹配），独立记录契约异常；权限副作用快照仅取唯一匹配行并用前后台单条详情校验，不把额外行算查询通过。

本地证据：[权限报告](results/permissions-20260910/report.md)、private-baseline.json（0600恢复基线）、private-state.json（0600请求与本轮快照）、review-access.json（A/B对照）、db-permission-evidence.json（只读SQL结果）。当前该会员保留一条A提交、普通角色B无法复核的申请供核查；无BUG建单、无群投递、无数据库写入。
