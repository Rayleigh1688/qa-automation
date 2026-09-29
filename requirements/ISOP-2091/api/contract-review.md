# ISOP-2091：FB接口契约核对（2026-09-29）

[开测与去重基线](../readiness-20260929.md) · [设计](../design.md)

来源：本机`/Users/rayleigh/API/FB/filbet/活动/`，HEAD与远端main同为`c3cf68d560c6d6c2100dd5705923680e6aeed51f`。已读厂商排行榜前台2份及后台3份接口文件；仅契约评审，未发业务请求。

| 能力 | 方法与路径 | 关键输入/输出 | 对应用例 |
| --- | --- | --- | --- |
| 前台详情 | GET `/promo/platform/rankings/detail` | pid=39；conf、platform_ranking、me/ranking、valid_bet、num、ty、bonus/token/fs | C01/C04/C05/C08 |
| 前台历史 | GET `/promo/platform/rankings/list` | pid=39、ymd、platform_name、last_id；d中的厂商/日期/排名/奖励/流水倍数 | C01/C04/C05/C06/C08 |
| 后台报表 | GET `/admin/promo/venue/rankings/report` | page/page_size及厂商、名次、会员、类型、时间筛选；total与d | C01/C04/C05/C06/C08/C09 |
| 报表导出 | GET `/admin/promo/venue/rankings/export` | 报表条件加topic_id；只返回ok，需要订阅/文件证据 | C08 |
| 活动编辑 | 文档POST `/admin/promo/update` | id=39、config.rankings/venue、multiple、popup_text、turnover_limit | C02/C03/C05/C06/C07 |

前台文件在`厂商排行榜/`；后台文件在`后台-活动管理/厂商排行榜/`。后台“详情.bru”实际文档内容为编辑，Bruno请求块却写GET，不能当成只读详情直接执行；保存前必须确认真实方法及完整请求。通用配置读取接口待按活动列表契约补映射。

## 分点核对，不阻塞全部测试

- 活动映射：Jira原型ID34，FB前后台id/pid39；2157评论17410已记录这一差异。请求先按文档39，通过活动名称、配置和报表记录核实，不将编号差异直接报为产品Bug。
- 奖励枚举：前台/配置/后台响应ty=0现金、1FS、2币；后台查询参数ty=1现金、2FS、3币。分开建立映射，用已知奖励记录验证筛选，不擅自统一枚举。详情conf中rotation_info注释ty=2与其余ty=1冲突，先查真实响应。
- 历史必填参数：Bruno请求块仅pid，docs还要求ymd/platform_name/last_id；不能原样运行该请求块后将空数据直接判Bug。首游标格式和日期范围按实际契约验证。
- 数据归属：历史有ymd；报表只示例created_at/stats_at，stats_at混称“统计日期和达标时间”。需要分别核结算日、达到最终分数时间、派奖时间，不拿创建时间替代结算时间。
- 排除配置：venue示例只有name/game_class/lower_limit/exclude_gid，未清晰描述厂商标识、整类排除及新增游戏继承；C02/C06需配置和注单独立对照。
- 次日生效/不回溯：示例未列当前与待生效配置或生效时间；实际配置读取、保存回执和跨日记录待查，不从保存成功推断规则通过。
- 流水与账变：流水倍数可读，但接口列表不足以证明流水生成、资产到账或重跑幂等；需补钱包/流水/FS结算记录和调度任务证据。TEST-3205/3193沿用旧单。
- 导出虽是GET仍可能创建异步任务，不能当普通只读探针；响应ok不是导出通过。
- Free Spin多选：TEST-3170已完成，原描述仅截图；先核多选对象与实际配置，再细化断言，不把“仅GAME层级”误解为必然只能单选游戏，也不据标题扩展为允许OPEN/PROVIDER。

尚无2091的plan.json/API参数矩阵或自动执行实现。上述映射可用于准备首轮请求，不宣称已经一键可跑；未核的字段不会被拼成虚构断言。
