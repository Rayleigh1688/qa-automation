# ISOP-2100：10月2日后台入口与申请条件复核

[前次链路执行](verification-20261001-chain.md) · [接口定位](chain-api-20261001.md)

2026-10-02约11:50（UTC+8）按用户要求核对各后台链接及相对10-01的变化。本轮仅检查已有入口、正常登录和只读申请条件；未继续注册、申请、审核、充值或投注。

| 环境 | 入口 | 地址 | 今日结果 |
| --- | --- | --- | --- |
| FAT | 管理后台 | [admin-fat.filbet2025.com](https://admin-fat.filbet2025.com/) | 根页面HTTP200，未换域跳转 |
| FAT | 代理管理后台 | [admin-agency-fat.filbet2025.com](https://admin-agency-fat.filbet2025.com/) | 根页面HTTP200；主测试账号fresh登录及只读配置查询成功 |
| FAT | 代理端 | [agency-fat.filbet2025.com](https://agency-fat.filbet2025.com/) | 根页面HTTP200，标题Filbet Affiliate；本轮未登录代理端重跑报表 |
| FAT | 合规后台 | [admin-pagcor-fat.filbet2025.com](https://admin-pagcor-fat.filbet2025.com/) | 根页面HTTP200，未换域跳转；本轮未登录 |
| UAT | 管理后台 | [admin-antd.filbet.zone](https://admin-antd.filbet.zone/) | 根页面HTTP200，与本地UAT配置一致；本轮未登录 |

配套FAT客户端为[client-fat.filbet2025.com](https://client-fat.filbet2025.com/)，今日根页面HTTP200，昨日新建A_new的fresh登录及会员/审核状态查询成功。代理管理后台供运营审核、设置代理；代理端供代理查看自己的会员和统计，是两个独立入口。

## 已核的变化范围

- **地址：** 上述已知入口均返回原域名页面；本地FAT/UAT配置与前批证据没有发现地址变化。不能将Bruno旧dev/admin环境中的`.filbet2025.com`地址机械当成当前UAT；本机UAT明确使用`.filbet.zone`。
- **昨日不可申请条件：** 同一A_new身份已内部核对，仍是`can_apply_agency=false`、`apply_agency_status=0`、`kyc_status=0`，审核结果仍为空。三项代理开关仍为`current=2 / target=1 / open_time=0`，与昨日完全一致。文档将current2解释为关闭；未证明此值就是不可申请的根因，不据target1认定已开启。
- **今日静态资源更新迹象：** 首页响应头Last-Modified分别标记FAT管理后台10-02 11:23:07、FAT代理端11:04:51、UAT管理后台11:30:18（均UTC+8）。当前入口脚本分别为`umi-43e8bd15.js`、`index-BXw_AQMu.js`、`umi-e1b62677.js`。这些是服务器提供的首页文件修改时间和当前资源名，不等于已核实具体功能修复或完整部署时间。
- **FB远端确有新提交：** main由本地`2b7ecef`推进到`59946fe92090ec97422b0d53d70fdc9933d50c71`，新增提交时间10-02 10:01:26 +08，标题`v`。只改后台代理统计报表、个人统计列表及个人统计查看三份契约：代理统计补六项指标及汇总字段，个人统计列表补`agency_upline_uid/name`，查看补`jp_winning`。环境文件/域名、代理端契约没有变化。通过隔离临时仓库读取，原FB工作区未pull且保持干净；详见[版本及指纹](../../reports/qa/ISOP-2100/20261002-entry-review/fb-source.json)。
- **功能及部署：** 本次未全量回归昨日管理页面缺项、下钻、导出、日期/脱敏及NGR小计问题；没有可比较的完整前后部署版本，不能断言今天没有任何代码发布或功能变化。

原始依据：[入口GET及页面标题](../../reports/qa/ISOP-2100/20261002-entry-review/entry-availability.json)、[昨日/今日申请条件对照](../../reports/qa/ISOP-2100/20261002-entry-review/readonly-diff/summary.json)。入口GET无认证，HTTP200不代表业务功能已验收；登录和条件查询未写入配置或业务数据，脱敏证据留Git忽略目录。

本地链接及差异检查无新增错误；`check:docs`仍仅报原有09-30交接链接缺目标。未执行全套单测、业务写入或资金门禁。
