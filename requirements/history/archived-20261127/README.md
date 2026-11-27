# 2026-11-27 需求归档

[历史索引](../README.md) · [当前需求](../../README.md#当前需求)

按用户决定，将 ISOP-2375 之前的 17 项当前需求移入本批。当前保留 ISOP-2375 和 ISOP-2393，历史实体共 56 项。设计、问题、用例、XMind、证据基线和未决事项随原目录保留，归档状态独立于需求完成、上线和测试结论。

默认发现、批量用例导出与自动工作流只处理当前需求；本批资料可用显式需求编号查询。报告输出位置沿用 `reports/qa/<需求编号>/`。本次目录迁移未执行 FAT/UAT 测试，也未清理执行产物。此前移出的原始证据见[同日执行产物退出记录](../README.md#cleanup-20261127)。

ISOP-2123 和 ISOP-2124 的证据基线仅因迁移后的相对链接更新而重绑文件哈希，仍为 PARTIAL，既有来源范围及结论保留。

| Jira 编号 | 需求名称 | 保留资料 |
| --- | --- | --- |
| ISOP-2123 | FILPLAY合规后台调整（旧样本与人数预期需重评） | [设计](ISOP-2123/design.md) · [问题](ISOP-2123/questions.md) · [36条用例](ISOP-2123/test-cases.md) · [CSV](ISOP-2123/cases.csv) · [XMind](ISOP-2123/ISOP-2123-测试用例.xmind) · [新规则影响](ISOP-2286/design.md#与既有需求的差异) |
| ISOP-2124 | FILPLAY合规项目盘点（正式用例需承接新KYC） | [设计](ISOP-2124/design.md) · [问题](ISOP-2124/questions.md) · [63条用例](ISOP-2124/test-cases.md) · [CSV](ISOP-2124/cases.csv) · [XMind](ISOP-2124/ISOP-2124-测试用例.xmind) · [新规则影响](ISOP-2286/design.md#与既有需求的差异) |
| ISOP-2214 | 过审礼金无法导出（W27评审） | [设计](ISOP-2214/design.md) · [问题](ISOP-2214/questions.md) · [测试重点](ISOP-2214/test-cases.md) |
| ISOP-2230 | 厂商排行榜活动优化（W27评审） | [设计](ISOP-2230/design.md) · [问题](ISOP-2230/questions.md) · [测试重点](ISOP-2230/test-cases.md) |
| ISOP-2232 | PT免费旋转串接（W27评审） | [设计](ISOP-2232/design.md) · [问题](ISOP-2232/questions.md) · [测试重点](ISOP-2232/test-cases.md) |
| ISOP-2233 | Pagcor責任博彩調整 | [设计](ISOP-2233/design.md) · [问题](ISOP-2233/questions.md) · [测试重点](ISOP-2233/test-cases.md) |
| ISOP-2234 | 代理后台新增推广链接（W27评审） | [设计](ISOP-2234/design.md) · [问题](ISOP-2234/questions.md) · [测试重点](ISOP-2234/test-cases.md) |
| ISOP-2238 | 图表Y轴展示不全（W27评审） | [设计](ISOP-2238/design.md) · [问题](ISOP-2238/questions.md) · [测试重点](ISOP-2238/test-cases.md) |
| ISOP-2239 | VCAT问题调整（W27评审） | [设计](ISOP-2239/design.md) · [问题](ISOP-2239/questions.md) · [测试重点](ISOP-2239/test-cases.md) |
| ISOP-2278 | [FILPLAY] 测试环境游戏对接（新建初评） | [设计](ISOP-2278/design.md) · [问题](ISOP-2278/questions.md) · [测试重点](ISOP-2278/test-cases.md) |
| ISOP-2281 | [FILPLAY] 功能测试走通（新建初评） | [设计](ISOP-2281/design.md) · [问题](ISOP-2281/questions.md) · [测试重点](ISOP-2281/test-cases.md) |
| ISOP-2286 | [FILPLAY] KYC调整（新建初评） | [设计](ISOP-2286/design.md) · [问题](ISOP-2286/questions.md) · [测试重点](ISOP-2286/test-cases.md) |
| ISOP-2289 | [FILPLAY] 充值、提现功能（新建初评） | [设计](ISOP-2289/design.md) · [问题](ISOP-2289/questions.md) · [测试重点](ISOP-2289/test-cases.md) |
| ISOP-2294 | [FILPLAY] 活动（待补正文） | [设计](ISOP-2294/design.md) · [问题](ISOP-2294/questions.md) · [测试重点](ISOP-2294/test-cases.md) |
| ISOP-2297 | [FILPLAY] 首页版面（待补正文） | [设计](ISOP-2297/design.md) · [问题](ISOP-2297/questions.md) · [测试重点](ISOP-2297/test-cases.md) |
| ISOP-2320 | [FILPLAY] 遊戲列表加上投注返水、輸返選項 | [设计](ISOP-2320/design.md) · [问题](ISOP-2320/questions.md) · [用例](ISOP-2320/test-cases.md) |
| ISOP-2341 | [FILPLAY] 遊戲橫豎屏優化 | [设计](ISOP-2341/design.md) · [问题](ISOP-2341/questions.md) · [用例](ISOP-2341/test-cases.md) |

## 原日期评审资料

- [2026-10-16 W27 八项评审](../../reviews/2026W27-20261016.md)与[2026-10-28 W27 增量](../../reviews/2026W27-20261028.md)记录了当日需求范围及未读来源。
- [2026-11-10 ISOP-2320／ISOP-2341 初评](../../reviews/2026-11-10-ISOP-2320-2341.md)和[2026-11-23 ISOP-2233 初评](../../reviews/2026-11-23-ISOP-2233.md)保留各次只读采集范围。
