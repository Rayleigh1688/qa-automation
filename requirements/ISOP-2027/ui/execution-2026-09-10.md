# ISOP-2027 FAT UI 读写实测（进行中）

> 留存说明（2026-09-11）：本文是原日期的文字结论。用户已授权删除旧结果、扫描和临时脚本，文内旧路径只表示历史来源，不能作为当前可复核/可导入证据；当前入口与保留范围见[清理记录](../../../docs/project-cleanup-2026-09-11.md)。

测试负责人Davinci。用户已确认FAT读写及边界测试；B保持用户指定的Codex角色，A为独立复核人。API准备的独立会员仅用于本轮UI，无资金操作、Jira写入或群发送。

证据目录：`reports/telegram/runs/isop2027-full-20260910/`；前后正式资料核对：`requirements/ISOP-2027/api/results/ui-fixture-20260910/`。页面定位配置：当前[isop2027.json](../../../ui/data/isop2027.json)（旧fat资产已删除）。

## 已执行

- B通过页面筛选本轮会员，确认编辑提示，打开表单。手机号、用户留言、KYC状态均为禁用控件。
- 未修改内容直接提交：弹出“No field or document changes”，无编辑请求。首次脚本只检查toast而未检查确认弹窗，定位失败；修正后验证通过，此前没有业务写入。
- B在UI修改姓名并提交，接口业务成功；独立API对账：唯一待复核，正式资料未变，草稿新值匹配UI输入。
- A在UI打开复核抽屉，同一差异行展示预先确认的旧姓名和新姓名。空原因点击驳回，被必填校验拦截且无复核请求。
- A在UI核准一次，业务成功；独立对账确认该申请转已核准，前后台三份正式姓名更新、其他字段不变，旧审计不改写且只追加一条。
- UI选择有效PNG 512001字节：显示大小提示且不上传；512000字节：允许上传并提供Restore。这两点通过，不代表已证明三图片全部保存/核准。

## 实际限制与下一步

Codex角色打开页面时`/admin/kyc/review/list`、`/admin/shop/gs/list`返回permission，记录于ui-execution.json的rejectedResponses。复核权限缺口见[权限API证据](../api/execution-permissions-2026-09-10.md)。门店下拉框不能凭空列表判通过。

继续三图片替换/还原、UI驳回闭环、已处理详情只读、筛选及权限可见性。无变更API接受临时图片URL变化的候选不能据此判UI也失败：本轮UI无变更拦截已通过。

## 图片还原异常

三个证件位分别上传成功，均出现Restore按钮。但普通点击还原被相邻按钮覆盖，Playwright报告pointer events intercepted；已按UI候选保留截图restore-dom.png。没有使用force点击，不能判还原通过。首次按角色精确名称查询未匹配按钮属于定位问题；改用文字定位后才得到实际遮挡证据。独立正常三图提交/驳回场景继续，不将本失败改判。

## 本地校验

`npm run check`的文档、归档、资产及语法检查通过；单元测试首次因沙箱禁止localhost监听报错。允许本机测试服务器后单独重跑`npm run test:unit`，233项通过。此校验不代表业务用例通过。

## 本轮后续结果

- 独立正常用例：B通过UI一次提交文字及三图片；请求与草稿三图片键逐一匹配，均不同于原图，正式资料未变。
- A通过UI填写正常原因驳回；三份正式资料保持原姓名和三张原图，申请转已驳回、原因完整保存，旧审计保留且仅追加一条。证据：ui-image-submit-execution.json、ui-reject-execution.json及API支撑check-images.py/check-reject.py。
- 已处理页按本轮UID筛选精确返回已核准/已驳回各一条，总数2。已处理详情无可再次核准或驳回的按钮。证据：ui-history-execution.json、ui-history-filter.json。
- 首次已处理筛选脚本捕获到了页面初始化响应；限定同UID且state=2后检查通过。三图上传首次固定等待造成时序错误；改为等待真实上传响应后完成独立正常用例。上述脚本问题未列入产品BUG。

## 尚未全覆盖

还原按钮普通点击失败；普通Codex角色复核及门店选项被权限阻塞。五状态完整矩阵、跨身份并发、各筛选组合、证件权限隔离、故障注入仍不算通过。API图片核准历史证据不能替代UI核准三图的证据。本轮完成的是姓名UI核准、三图及文字UI驳回两个闭环和列出的局部边界。

## 三图片UI核准闭环

独立新会员`api/results/ui-images-approve-20260910/`：B在UI提交姓名和三张有效PNG，A在UI核准。草稿与实际请求逐项匹配，复核前正式资料不变；核准后前后台三份正式姓名和图片键均与UI请求一致，其他字段/KYC状态不变，唯一申请进入已核准，旧审计不变且追加一条。

UI证据：ui-images-approve-submit.json、ui-images-approve-execution.json。独立对账：check-draft.py、check-final.py及result.json。本轮三图UI核准和三图UI驳回均有实际闭环证据。

- `ui-preview-execution.json`：三组前后图片共六个预览均打开、实际加载并用Escape关闭。初次直接点击img被图片自身预览遮罩拦截，改为点击可交互图片容器后通过；不同于Restore被相邻按钮遮挡，不列为产品BUG。
