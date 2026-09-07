# 已完成接口扫描资产索引

归档日期：2026-09-07。这里保存已有扫描成果，不是当前可执行 P0 门禁，也不是新需求测试必须完成的前置工作。

| 资产 | 说明入口 | 主要证据 |
| --- | --- | --- |
| FAT 客户端 | [扫描说明](2026-09-07/fat-client-interface-scan/README.md) | [接口汇总](2026-09-07/fat-client-interface-scan/results/fat-client-endpoint-summary.csv) |
| FAT 管理后台 | [扫描说明](2026-09-07/fat-admin-interface-scan/README.md) | [合并报告](2026-09-07/fat-admin-interface-scan/results/member-gap-merged-report.md) |
| 合规管理后台 | [扫描说明](2026-09-07/pagcor-admin-interface-scan/README.md) | [结果报告](2026-09-07/pagcor-admin-interface-scan/results/pagcor-admin-report.md) |
| 代理管理后台 | [扫描说明](2026-09-07/agency-admin-interface-scan/README.md) | [结果报告](2026-09-07/agency-admin-interface-scan/results/agency-admin-report.md) |
| 代理前台 | [扫描说明](2026-09-07/agency-portal-interface-scan/README.md) | [结果报告](2026-09-07/agency-portal-interface-scan/results/agency-portal-report.md) |
| 客户端控件参考 | [控件说明](2026-09-07/client-button-map/README.md) | 本地截图随目录移动，仍被 Git 忽略 |
| 发现汇总与分类 | [历史专项说明](2026-09-07/interface-discovery/README.md) | [分类汇总](2026-09-07/interface-discovery/current-interface-comparison.md) |

## 归档边界

- 235 份非忽略文件有 [校验清单](2026-09-07/manifest.json)，记录原路径、新路径、迁移前后 SHA-256。13 份被忽略的本地文件一并移动并保留忽略属性，不因此加入版本控制。
- 历史数据和脚本原文保留；只调整部分 Markdown 链接。脚本中的旧 cwd、输出路径、账号前置和命令属于历史语境，不能从仓库根目录直接重跑。恢复专项时先迁移路径、重新分配数据并验证契约。
- 历史报告中的旧路径字符串、失效状态与时间戳不代表当前环境；按此索引的新目录定位证据。
- 正式接口定义与检索继续使用 [inventory](../../api/inventory/README.md)、[catalog](../../api/catalog/README.md)。P0 使用原有用例与 runner，不读取本归档来判定本次通过。
- `npm run check:archive` 检查清单完整性、内容哈希与旧目录是否残留；归档不再持续生成或累计新扫描。

后续主线：[新需求 AI 测试设计](../../requirements/README.md)。低风险低频接口随需求按影响补充，涉及资金、权限或不可逆数据操作仍按风险评估。
