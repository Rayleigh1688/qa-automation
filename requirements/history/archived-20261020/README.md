# 2026-10-20需求归档

[历史索引](../README.md) · [当前需求](../../README.md) · [静态图片清理记录](../../../docs/project-cleanup-2026-10-20.md)

依据用户2026-10-20“2090可以归档了”决定，ISOP-2090输值返利活动实体移至本批目录，退出默认发现、批量导出及自动工作流。当前范围保留8项W27需求，历史需求实体共39项。

| Jira | 保留资料 | 结论与边界 |
| --- | --- | --- |
| [ISOP-2090](https://alibaba-international.atlassian.net/browse/ISOP-2090) | [设计](ISOP-2090/design.md) · [问题](ISOP-2090/questions.md) · [23张功能卡](ISOP-2090/test-cases.md) · [总表](ISOP-2090/cases.csv) · [测试顺序](ISOP-2090/execution-order.md) · [CLI](ISOP-2090/api/README.md) · [10-16复测（原记录已退出）](ISOP-2090/questions.md#history-results-20261022) · [缺陷评审（原记录已退出）](ISOP-2090/questions.md#history-results-20261022) | 10-16 FAT发现业务异常，完整验收未完成；来源仍为PARTIAL。归档不关闭候选、不改FAIL／NOT_RUN或补造PASS |

迁移完整保留工作区已有代码、用例及10-16未提交记录。CLI参数、业务守卫及`reports/qa/ISOP-2090/`输出路径保持；显式需求编号仍可定位历史目录，5个直接Python入口改从本归档目录调用。归档不主动重放登录、配置、资金或恢复操作，也未修改Jira或发送群通知。

目录内“当前”“下一步”“本轮”按原记录日期理解，未完成项只是再次明确范围后回归的历史输入。10-12原始报告在本轮前已缺失，不算本次删除；10-20当时保留仍关联缺陷、导出及结果索引的关键图片，该日只删除4张过渡／重复截图，具体文件、依赖判断与保留项见[清理记录](../../../docs/project-cleanup-2026-10-20.md)，删除不改变原始业务结论。

2026-10-22用户进一步授权清除历史API／功能执行结果，10-16余下原始报告／图片／导出和本单日期执行／缺陷评审报告已退出；必要规则、失败和未完成范围收敛到[日期摘要](ISOP-2090/questions.md#history-results-20261022)。三次已完成恢复链、别名及最小业务定位保留于忽略的`api/local-state/retained/ISOP-2090/20261016-retest/`，不重放旧资金／配置；详见[后续清理记录](../../../docs/project-cleanup-2026-10-22.md)。
