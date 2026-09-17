# 当前班车状态

2026-09-16补充：[14个Story及42个子任务的提测时间与完整状态历史](submission-history-20260916.md)已实时核对。下表仍为9月15日班车快照；最新Jira差异见补充记录，不能继续将其中「未提测」直接当作当前Jira结论。执行暂停和范围约定不由状态历史自动解除。

同步日期：2026-09-15。来源：[2026年9月第二次班车](https://alibaba-international.atlassian.net/wiki/spaces/QT/pages/418938887/2026-9)（页面标注同步日期2026-09-14；本次浏览器已读14行）及14张Jira当前状态（更新于2026-09-15 17:27，UTC+8）。

**执行约定：待上线的需求本轮不再测试。** 共6项暂停：2027、2029、2037、2038、2110、2086。2032仅管理后台已提测，客户端先不测；未提测项等待提测。状态同步不修改已有API/UI结果，也不等同于生产发布。

[状态页面](status.html) · [上轮测试记录](test-round-20260914-seven.md) · [历史状态](status-history-20260914.md)

| 需求 | 班车状态 | Jira状态 | 本轮处理 |
| --- | --- | --- | --- |
| [ISOP-2022](https://alibaba-international.atlassian.net/browse/ISOP-2022) | 测试中 | FAT 测试 | 数据库表需要重建；重建及修复就绪后再执行可测API |
| [ISOP-2027](https://alibaba-international.atlassian.net/browse/ISOP-2027) | 待上线 | 待上线 | 本轮不再测试 |
| [ISOP-2028](https://alibaba-international.atlassian.net/browse/ISOP-2028) | 未提测 | 待办 | 等待正式提测 |
| [ISOP-2029](https://alibaba-international.atlassian.net/browse/ISOP-2029) | 待上线 | 待上线 | 本轮不再测试 |
| [ISOP-2030](https://alibaba-international.atlassian.net/browse/ISOP-2030) | 需求调整 | 審查失敗 | 暂停；等待调整后重新明确范围 |
| [ISOP-2031](https://alibaba-international.atlassian.net/browse/ISOP-2031) | 待验收 | 待办 | 生产验收由人工推进；不从父单待办推断需重测 |
| [ISOP-2032](https://alibaba-international.atlassian.net/browse/ISOP-2032) | 部分提测 | 待办 | 仅管理后台已提测；客户端未提测，先不测客户端 |
| [ISOP-2037](https://alibaba-international.atlassian.net/browse/ISOP-2037) | 待上线 | 待上线 | 本轮不再测试 |
| [ISOP-2038](https://alibaba-international.atlassian.net/browse/ISOP-2038) | 待上线 | 待上线 | 本轮不再测试 |
| [ISOP-2041](https://alibaba-international.atlassian.net/browse/ISOP-2041) | 待确认 | 已完成 | Jira已完成；班车验收结论仍待确认，不自动视作已上线 |
| [ISOP-2043](https://alibaba-international.atlassian.net/browse/ISOP-2043) | 未提测 | 待办 | 等待表完成及正式提测 |
| [ISOP-2072](https://alibaba-international.atlassian.net/browse/ISOP-2072) | 未提测 | 待办 | 等待正式提测 |
| [ISOP-2110](https://alibaba-international.atlassian.net/browse/ISOP-2110) | 待上线 | 验收通过 | Jira验收通过；按班车待上线，本轮不再测试 |
| [ISOP-2086](https://alibaba-international.atlassian.net/browse/ISOP-2086) | 待验收 | 待上线 | Jira已待上线；按用户要求本轮不再测试，保留班车待验收差异 |

2086班车待验收、Jira待上线，本轮按用户待上线不测处理；2110班车待上线、Jira验收通过；2041班车待确认、Jira已完成；2031班车待验收、Jira待办。差异并列，不用父单状态覆盖班车细分范围。2070未列入本次14项，旧状态保留。

本地HTML状态通过`npm run qa -- status --serve`查看。班车阶段保存为带来源的独立状态修订，API/UI记录原样保留；待上线项同时在执行配置中暂停。独立旧CLI仍可显式调用，但本轮约定不再选择这些需求。
