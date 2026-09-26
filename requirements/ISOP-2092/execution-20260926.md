# ISOP-2092：按用例逐点执行清单（2026-09-26）

[原始用例](test-cases.md) · [实测分析](verification-20260926.md) · [可筛选报告](../../reports/qa/ISOP-2092/20260926-data-analysis/results.html)

本清单将原C01—C08拆为具体测试点，沿用2026-09-26 FAT实测证据，是离线整理，不是新一轮运行。通过仅对本行范围有效；失败也表示本项已经执行。待核验表示已做对照但依据或数据链不足，不能算通过或直接归为产品失败。未执行表示缺少该项执行证据。测试点数不等于请求次数、独立缺陷数或整条需求通过率。

**共64个测试点：通过 29 项；失败 15 项；待核验 12 项；未执行 8 项。已执行56项。**

## 谁来做

已执行项的执行人均为Codex（自动化UI/API或只读数据核算），没有记成人工PASS。当前没有必须由你亲自重跑的功能项。未执行项由Codex补测；依赖开发提供Doris映射、导出恢复，或产品确定规则的项，写在每行下一步。建议你可选做一次批准设计附件与实际页面的人工视觉验收（C01-05）；它尚未执行，不影响已完成数据测试的登记。

未执行项是后续执行清单，不要求你代执行；这次整理不会把未做项目补记成通过。原8条复合场景状态保留兼容，逐点结论以本表为准。问题F01—F11、源单差额D01—D05的解释见实测分析。

## 用例结果总览

| 原用例 | 通过 | 失败 | 待核验 | 未执行 |
| --- | ---: | ---: | ---: | ---: |
| [C01 页面和提示](#c01) | 2 | 2 | 0 | 1 |
| [C02 日期与注册人数](#c02) | 3 | 0 | 0 | 2 |
| [C03 日期边界与参数](#c03) | 3 | 1 | 2 | 0 |
| [C04 图表、明细和导出](#c04) | 11 | 6 | 2 | 2 |
| [C05 首充、复充与充值](#c05) | 3 | 0 | 3 | 1 |
| [C06 跨日人数与人均值](#c06) | 2 | 3 | 1 | 1 |
| [C07 投注、派彩和GGR](#c07) | 3 | 1 | 1 | 1 |
| [C08 充提差、投充比与源单](#c08) | 2 | 2 | 3 | 0 |

<a id="c01"></a>
## C01：页面和提示

| 测试点 | 结果 / 执行 | 预期 | 实际结果 | 下一步 / 由谁处理 | 证据 |
| --- | --- | --- | --- | --- | --- |
| **C01-01 三组卡片、指标与分组** | **通过** / 已执行（Codex） | 首页显示要求的指标分组，卡片可对应指标 | 已扫描29张卡片及三类下钻分组；本项不含附件像素级验收 | 无需你重复执行；后续版本按需回归；Codex | [ui-comprehensive-settled.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-comprehensive-settled.json)、[home-current.png](../../reports/qa/ISOP-2092/20260926-data-analysis/home-current.png) |
| **C01-02 17个说明提示可正常悬停** | **通过** / 已执行（Codex） | 正常鼠标悬停能看到对应说明 | 1440宽度17个入口可用；有争议的业务文案不在本项判定 | 无需你重复执行；后续版本按需回归；Codex | [tooltips.json](../../reports/qa/ISOP-2092/20260926-data-analysis/tooltips.json) |
| **C01-03 复充金额提示在常用宽度可操作** | **失败** / 已执行（Codex） | 1440宽度正常hover可显示提示 | 副标题遮挡问号，正常hover失败；1920宽度可以显示（F05） | 开发修复后由Codex回归；开发 → Codex | [tooltips.json](../../reports/qa/ISOP-2092/20260926-data-analysis/tooltips.json)、[ui-chart-values.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-chart-values.json)、[tooltip-viewport-1440.png](../../reports/qa/ISOP-2092/20260926-data-analysis/tooltip-viewport-1440.png)、[tooltip-viewport-1920.png](../../reports/qa/ISOP-2092/20260926-data-analysis/tooltip-viewport-1920.png) |
| **C01-04 零金额仍保留两位小数** | **失败** / 已执行（Codex） | 金额为0显示整数0；比例允许0.00% | 零金额显示0.00，与金额规则不符（F01）；比例0.00%可接受，不列失败。C08共用金额结果 | 开发修复后由Codex回归；开发 → Codex | [zero-day.png](../../reports/qa/ISOP-2092/20260926-data-analysis/zero-day.png)、[ui-focused.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-focused.json) |
| **C01-05 按TLSQ布局附件做人工视觉验收** | **未执行** / 未执行（—） | 页面布局与批准的附件一致 | 附件尚未独立视觉复核；自动化截图不能登记为人工PASS | 可选人工验收：打开批准附件，对照首页与弹窗；记录差异截图。不是要求你重跑数据测试；用户（可选人工验收） | 无该项执行证据 |

<a id="c02"></a>
## C02：日期与注册人数

| 测试点 | 结果 / 执行 | 预期 | 实际结果 | 下一步 / 由谁处理 | 证据 |
| --- | --- | --- | --- | --- | --- |
| **C02-01 普通日期点击六个快捷项** | **通过** / 已执行（Codex） | UTC+8今日/昨日/本周/上周/本月/上月回填正确 | 09-26实际点击及请求已核；只证明该点击日 | 无需你重复执行；后续版本按需回归；Codex | [ui-comprehensive-settled.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-comprehensive-settled.json)、[api-comprehensive.json](../../reports/qa/ISOP-2092/20260926-data-analysis/api-comprehensive.json) |
| **C02-02 87个单日注册人数对账** | **通过** / 已执行（Codex） | 接口人数等于UTC+8注册源记录计数 | 07-01—09-25共87日全部一致 | 无需你重复执行；后续版本按需回归；Codex | [registrations-mismatches.json](../../reports/qa/ISOP-2092/20260926-data-analysis/registrations-mismatches.json)、[registrations.tsv](../../reports/qa/ISOP-2092/20260926-data-analysis/registrations.tsv) |
| **C02-03 三个月、两个月、一个月累计查询** | **通过** / 已执行（Codex） | 查询区间回填正确；可加字段等于单日累加 | 7/1、8/1、9/1起至9/25，22个可加字段及7月、8月、9月单月均内部一致；源单正确性另列 | 无需你重复执行；后续版本按需回归；Codex | [ui-periods.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-periods.json)、[arithmetic.json](../../reports/qa/ISOP-2092/20260926-data-analysis/arithmetic.json) |
| **C02-04 周一当天点击本周/上周** | **未执行** / 未执行（—） | 周一起止与UTC+8一致 | 本轮未推进测试时钟到周一，普通日期通过不能替代此项 | Codex补受控时钟场景，或09-28当天复测；不要求你手动等待；Codex | 无该项执行证据 |
| **C02-05 月初当天点击本月/上月** | **未执行** / 未执行（—） | 跨月、跨年边界按当前点击日计算 | 本轮未推进时钟到月初 | Codex补月初/跨年时钟场景；不需要你重复当前日期六快捷项；Codex | 无该项执行证据 |

<a id="c03"></a>
## C03：日期边界与参数

| 测试点 | 结果 / 执行 | 预期 | 实际结果 | 下一步 / 由谁处理 | 证据 |
| --- | --- | --- | --- | --- | --- |
| **C03-01 自定义89个自然日** | **通过** / 已执行（Codex） | 少于90天可以查询 | 06-29—09-25，UI/API均成功 | 无需你重复执行；后续版本按需回归；Codex | [ui-date-boundaries.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-date-boundaries.json) |
| **C03-02 自定义恰好90个自然日** | **失败** / 已执行（Codex） | 按现有小于90天规则拒绝 | 06-28—09-25，UI/API均放行（F02）；尚无改成≤90天的决定 | 开发修复后由Codex回归；开发 → Codex | [ui-date-boundaries.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-date-boundaries.json)、[threshold-api.json](../../reports/qa/ISOP-2092/20260926-data-analysis/threshold-api.json) |
| **C03-03 API拒绝91个自然日** | **通过** / 已执行（Codex） | 超过上限拒绝 | 直接请求91日，接口返回超过90天提示 | 无需你重复执行；后续版本按需回归；Codex | [api-comprehensive.json](../../reports/qa/ISOP-2092/20260926-data-analysis/api-comprehensive.json) |
| **C03-04 UI输入91天的交互** | **待核验** / 已执行（Codex） | 非法区间应清楚提示且不能误查 | UI把06-27起改回06-28，实际查询90日；90日放行已在上一项失败，自动回退交互是否合规尚无依据 | 产品明确提示/回退交互后Codex判定，避免重复算90日缺陷；开发/产品 → Codex | [ui-date-boundaries.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-date-boundaries.json) |
| **C03-05 反向日期、自定义缺少日期** | **待核验** / 已执行（Codex） | 异常参数应有明确契约 | 反向日期返回成功但空字段；自定义缺日期返回成功及历史值，已留证 | 开发说明参数默认与校验契约后Codex回归；开发/产品 → Codex | [api-comprehensive.json](../../reports/qa/ISOP-2092/20260926-data-analysis/api-comprehensive.json) |
| **C03-06 未知日期类型、全部参数缺失** | **通过** / 已执行（Codex） | 无效请求应拒绝 | 两类请求均被拒绝 | 无需你重复执行；后续版本按需回归；Codex | [api-comprehensive.json](../../reports/qa/ISOP-2092/20260926-data-analysis/api-comprehensive.json) |

<a id="c04"></a>
## C04：图表、明细和导出

| 测试点 | 结果 / 执行 | 预期 | 实际结果 | 下一步 / 由谁处理 | 证据 |
| --- | --- | --- | --- | --- | --- |
| **C04-01 29张卡片下钻到对应指标** | **通过** / 已执行（Codex） | 所点卡片对应最终请求指标和明细分组 | 29项映射及三分组已核；不代表全部数值通过 | 无需你重复执行；后续版本按需回归；Codex | [ui-comprehensive-settled.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-comprehensive-settled.json) |
| **C04-02 29项日图接口的数据点** | **通过** / 已执行（Codex） | 范围内每天一个点，与首页单日对应值一致 | 每项87点；精度差异单列，基础金额/人数/余额对照一致；不含月度聚合 | 无需你重复执行；后续版本按需回归；Codex | [api-comparison.json](../../reports/qa/ISOP-2092/20260926-data-analysis/api-comparison.json)、[api-comprehensive.json](../../reports/qa/ISOP-2092/20260926-data-analysis/api-comprehensive.json) |
| **C04-03 今日、昨日默认趋势窗口** | **通过** / 已执行（Codex） | 分别显示对应7日趋势窗口 | 两快捷项下钻得到7日窗口并正常加载 | 无需你重复执行；后续版本按需回归；Codex | [ui-comprehensive-settled.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-comprehensive-settled.json) |
| **C04-04 本周、上周默认趋势窗口** | **待核验** / 已执行（Codex） | 按Q-01明确的周窗口展示 | 已观察到08-24—09-27及08-17—09-20，均五周；目标端点尚待定 | 产品明确周窗口端点后Codex判定；开发/产品 → Codex | [ui-comprehensive-settled.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-comprehensive-settled.json) |
| **C04-05 本月默认趋势可加载** | **失败** / 已执行（Codex） | 默认窗口应在接口允许范围内，能正常显示 | 04-01—09-30共183日，最终请求被180天上限拒绝（F08） | 开发修复后由Codex回归；开发 → Codex | [ui-comprehensive-settled.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-comprehensive-settled.json) |
| **C04-06 上月默认趋势可加载** | **失败** / 已执行（Codex） | 默认窗口能正常显示 | 03-01—09-30共214日，最终请求被180天上限拒绝（F08同一问题） | 开发修复后由Codex回归；开发 → Codex | [ui-comprehensive-settled.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-comprehensive-settled.json) |
| **C04-07 图表180天上限** | **通过** / 已执行（Codex） | 180天可查，181天拒绝 | 两组边界结果符合接口上限 | 无需你重复执行；后续版本按需回归；Codex | [api-comprehensive.json](../../reports/qa/ISOP-2092/20260926-data-analysis/api-comprehensive.json) |
| **C04-08 明细分页完整性** | **通过** / 已执行（Codex） | 查询87天无重复、遗漏日期 | 9页共87个唯一日期 | 无需你重复执行；后续版本按需回归；Codex | [api-comparison.json](../../reports/qa/ISOP-2092/20260926-data-analysis/api-comparison.json) |
| **C04-09 明细六组API排序** | **通过** / 已执行（Codex） | 日期、充值金额、GGR各升/降序正确 | 六组排序全部符合方向 | 无需你重复执行；后续版本按需回归；Codex | [api-comparison.json](../../reports/qa/ISOP-2092/20260926-data-analysis/api-comparison.json)、[api-comprehensive.json](../../reports/qa/ISOP-2092/20260926-data-analysis/api-comprehensive.json) |
| **C04-10 UI下一页、切换指标、重置** | **通过** / 已执行（Codex） | 控件触发对应查询和状态更新 | 下一页发page=2；切换ARPU及重置到今日已验证 | 无需你重复执行；后续版本按需回归；Codex | [ui-controls-recheck.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-controls-recheck.json) |
| **C04-11 日/周/月切换控件响应** | **通过** / 已执行（Codex） | 点击后切换聚合展示 | 三个单位均可切换，前端聚合不另发API；数值正确性另列 | 无需你重复执行；后续版本按需回归；Codex | [ui-controls-recheck.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-controls-recheck.json) |
| **C04-12 周图各类指标聚合值** | **未执行** / 未执行（—） | 金额累计，余额取期末，比率/人均依分子分母计算 | 已操作周切换，但未逐项独立核对周图悬浮值 | Codex补周图数值核算；人均分母规则需先明确；Codex | 无该项执行证据 |
| **C04-13 首页及日图取结束日余额** | **通过** / 已执行（Codex） | 跨日余额使用结束日快照 | 三组累计与09-25余额一致；只证明接口选值，不证明底层快照全量 | 无需你重复执行；后续版本按需回归；Codex | [ui-periods.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-periods.json)、[api-comparison.json](../../reports/qa/ISOP-2092/20260926-data-analysis/api-comparison.json) |
| **C04-14 明细会员余额** | **失败** / 已执行（Codex） | 应与对应日期余额一致 | detail缺balance字段，表格各日显示0.00；09-25首页约13.82亿（F06） | 开发修复后由Codex回归；开发 → Codex | [ui-comprehensive-settled.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-comprehensive-settled.json)、[api-comprehensive.json](../../reports/qa/ISOP-2092/20260926-data-analysis/api-comprehensive.json) |
| **C04-15 月图会员余额** | **失败** / 已执行（Codex） | 每月取期末余额 | 8月显示42759376083.8026，等于31个日余额之和；期末应1381182935.5696（F09） | 开发修复后由Codex回归；开发 → Codex | [ui-chart-values.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-chart-values.json)、[monthly-balance-tooltip.png](../../reports/qa/ISOP-2092/20260926-data-analysis/monthly-balance-tooltip.png) |
| **C04-16 月图小数与大数轴展示** | **失败** / 已执行（Codex） | 金额清楚可读，避免浮点尾数和裁切 | 余额显示34574439520.560005，左侧纵轴大数裁切（F09/F10附属显示问题） | 开发修复后由Codex回归；开发 → Codex | [monthly-balance-tooltip.png](../../reports/qa/ISOP-2092/20260926-data-analysis/monthly-balance-tooltip.png)、[ui-chart-values.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-chart-values.json) |
| **C04-17 UI导出会员/投注分组** | **失败** / 已执行（Codex） | 点击Export应发起导出并有反馈 | 两分组按钮可点但无请求、下载或反馈（F11） | 开发修复后由Codex回归；开发 → Codex | [ui-comprehensive-settled.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-comprehensive-settled.json)、[ui-controls-recheck.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-controls-recheck.json)、[export-ui.png](../../reports/qa/ISOP-2092/20260926-data-analysis/export-ui.png) |
| **C04-18 API导出ty=1任务受理** | **通过** / 已执行（Codex） | 合法导出请求应受理 | HTTP200/status=true/data=ok；仅受理通过，未证明文件生成 | 无需你重复执行；后续版本按需回归；Codex | [api-export.json](../../reports/qa/ISOP-2092/20260926-data-analysis/api-export.json) |
| **C04-19 紧接导出ty=2** | **待核验** / 已执行（Codex） | 明确任务锁定时应如何处理 | 返回status=false / HomeBIDetail lock failed，已停止后续调用；不能当导出成功 | 开发核导出任务状态/锁规则后Codex重测；不以继续调用掩盖此次失败；开发/产品 → Codex | [api-export.json](../../reports/qa/ISOP-2092/20260926-data-analysis/api-export.json) |
| **C04-20 导出ty=3与三种文件内容** | **未执行** / 未执行（—） | 任务完成并取得文件，列顺序及数据与页面一致 | ty=3未调用；未获得文件，内容、完成通知均未验收 | Codex在导出任务恢复后补跑、下载和核文件；Codex | 无该项执行证据 |
| **C04-21 无token/无效token访问保护** | **通过** / 已执行（Codex） | basic/detail/chart均不泄露统计 | 共6组请求全部拒绝有效业务数据 | 无需你重复执行；后续版本按需回归；Codex | [api-comprehensive.json](../../reports/qa/ISOP-2092/20260926-data-analysis/api-comprehensive.json) |

<a id="c05"></a>
## C05：首充、复充与充值

| 测试点 | 结果 / 执行 | 预期 | 实际结果 | 下一步 / 由谁处理 | 证据 |
| --- | --- | --- | --- | --- | --- |
| **C05-01 87日首充金额** | **通过** / 已执行（Codex） | 第一笔Completed充值对应首充到账金额 | Completed且gt=1的paid_amount与87日接口一致 | 无需你重复执行；后续版本按需回归；Codex | [deposit-formulas.json](../../reports/qa/ISOP-2092/20260926-data-analysis/deposit-formulas.json) |
| **C05-02 已明确同日gt=2/3复充样本** | **通过** / 已执行（Codex） | 首充当日符合分类的后续完成充值计入复充 | 87日结果与同日gt=2/3到账汇总一致；本项不包含gt=0排除的正确性 | 无需你重复执行；后续版本按需回归；Codex | [deposit-formulas.json](../../reports/qa/ISOP-2092/20260926-data-analysis/deposit-formulas.json) |
| **C05-03 同日gt=0是否漏计复充** | **待核验** / 已执行（Codex） | 既有规则gt!=1且首充日相同应纳入 | 09-23后续到账650，接口仅100；差550恰是gt=0（D01） | 开发核gt=0业务含义/加工映射，再按既有规则判断缺陷；不能用观测值改规则；开发/产品 → Codex | [deposit-formulas.json](../../reports/qa/ISOP-2092/20260926-data-analysis/deposit-formulas.json)、[deposits.tsv](../../reports/qa/ISOP-2092/20260926-data-analysis/deposits.tsv) |
| **C05-04 A/B/C隔离人群及首充/复充人数** | **未执行** / 未执行（—） | 完整覆盖同日多笔、次日续充、历史首充会员，人数去重且金额正确 | 原用例A/B/C是设计示例，未实际按该组造数/逐人闭环；金额汇总证据不替代人数断言 | Codex优先找可追溯历史样本，不足再用已授权P0准备受控样本；Codex | 无该项执行证据 |
| **C05-05 8月、9月充值到账金额源单对账** | **通过** / 已执行（Codex） | 累计充值等于对应完成充值到账金额 | 8月15988、9月61930均一致；日级86/87日一致 | 无需你重复执行；后续版本按需回归；Codex | [deposits-mismatches.json](../../reports/qa/ISOP-2092/20260926-data-analysis/deposits-mismatches.json)、[deposits.tsv](../../reports/qa/ISOP-2092/20260926-data-analysis/deposits.tsv) |
| **C05-06 07-03充值差额** | **待核验** / 已执行（Codex） | 充值应能逐单解释 | 接口1600，当前源单完成到账1360，差240（D02） | 开发提供Doris入库/历史修订对应关系，Codex继续对账；开发/产品 → Codex | [deposits-mismatches.json](../../reports/qa/ISOP-2092/20260926-data-analysis/deposits-mismatches.json) |
| **C05-07 充值成功率源单对账** | **待核验** / 已执行（Codex） | 分子分母的状态与时间归属有依据 | 8个日期与当前源表状态数量计算不一致，未证明是同步还是统计缺陷 | 开发说明统计时点和状态回写后Codex复算；开发/产品 → Codex | [deposit-formulas.json](../../reports/qa/ISOP-2092/20260926-data-analysis/deposit-formulas.json) |

<a id="c06"></a>
## C06：跨日人数与人均值

| 测试点 | 结果 / 执行 | 预期 | 实际结果 | 下一步 / 由谁处理 | 证据 |
| --- | --- | --- | --- | --- | --- |
| **C06-01 单日ARPU/ARPPU公式** | **通过** / 已执行（Codex） | 分别为充值/登录人数、充值/充值人数 | 09-25：1200/8=150，1200/1=1200；底层人数完整性另列 | 无需你重复执行；后续版本按需回归；Codex | [daily-api.json](../../reports/qa/ISOP-2092/20260926-data-analysis/daily-api.json) |
| **C06-02 两日查询隐藏登录/投注人数** | **失败** / 已执行（Codex） | 非单日不展示只适用于当日的人数 | 09-23—24仍显示登录10、投注4，取结束日人数（F03） | 开发修复后由Codex回归；开发 → Codex | [ui-focused.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-focused.json)、[threshold-api.json](../../reports/qa/ISOP-2092/20260926-data-analysis/threshold-api.json) |
| **C06-03 3天及以上隐藏登录/投注人数** | **通过** / 已执行（Codex） | 跨日隐藏上述两项人数 | 3至90天已取多个阈值；页面三日显示--；不代表两日正确 | 无需你重复执行；后续版本按需回归；Codex | [threshold-api.json](../../reports/qa/ISOP-2092/20260926-data-analysis/threshold-api.json)、[ui-focused.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-focused.json) |
| **C06-04 两日ARPU/ARPPU与充值人数** | **待核验** / 已执行（Codex） | 区间分子和分母应对应同一统计范围 | 充值1862是两日累计，登录10/充值人数2为结束日；ARPU186.2、ARPPU931；目标应隐藏还是区间去重尚待Q-03 | 产品明确跨日展示及去重规则，开发修复后Codex验算；开发/产品 → Codex | [threshold-api.json](../../reports/qa/ISOP-2092/20260926-data-analysis/threshold-api.json) |
| **C06-05 月图ARPU** | **失败** / 已执行（Codex） | 人均值不能直接把每日人均相加 | 8月1161.6466503265、9月4267.258606347099，均为每日ARPU之和（F10）；目标分母仍需Q-03 | 开发修复后由Codex回归；开发 → Codex | [ui-derived-chart.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-derived-chart.json)、[monthly-ARPU.png](../../reports/qa/ISOP-2092/20260926-data-analysis/monthly-ARPU.png) |
| **C06-06 月图ARPPU** | **失败** / 已执行（Codex） | 月度人均充值不能累加每日人均 | 8月4020.55、9月26911.999999999796，为每日ARPPU之和（F10） | 开发修复后由Codex回归；开发 → Codex | [ui-arppu-chart.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-arppu-chart.json)、[monthly-ARPPU.png](../../reports/qa/ISOP-2092/20260926-data-analysis/monthly-ARPPU.png) |
| **C06-07 历史登录/投注人数独立去重** | **未执行** / 未执行（—） | 独立事件清单按日/区间重算，核对分母 | 未取得完整历史登录事件及Doris去重链；当前last_login不能倒推历史 | 开发提供事件/去重口径后Codex核算；开发 → Codex | 无该项执行证据 |

<a id="c07"></a>
## C07：投注、派彩和GGR

| 测试点 | 结果 / 执行 | 预期 | 实际结果 | 下一步 / 由谁处理 | 证据 |
| --- | --- | --- | --- | --- | --- |
| **C07-01 FS公司视角金额** | **通过** / 已执行（Codex） | 对应免费旋转源单的公司视角金额 | 87个单日可与bet_type=2源汇总对应 | 无需你重复执行；后续版本按需回归；Codex | [source-bets-sport-authoritative.json](../../reports/qa/ISOP-2092/20260926-data-analysis/source-bets-sport-authoritative.json) |
| **C07-02 Jackpot Winning金额** | **通过** / 已执行（Codex） | 对应奖池派彩源记录 | 87个单日与bet_type=3的jp_winning汇总一致 | 无需你重复执行；后续版本按需回归；Codex | [source-bets-sport-authoritative.json](../../reports/qa/ISOP-2092/20260926-data-analysis/source-bets-sport-authoritative.json) |
| **C07-03 7月、9月总GGR与七类之和** | **通过** / 已执行（Codex） | 总数等于分类合计 | 这两个月内部合计一致；不代表所有源单已对平 | 无需你重复执行；后续版本按需回归；Codex | [arithmetic.json](../../reports/qa/ISOP-2092/20260926-data-analysis/arithmetic.json) |
| **C07-04 8月总GGR与七类之和** | **失败** / 已执行（Codex） | 总数应等于七类合计 | 总数-379819.395，分类-379819.195，差-0.20；含8月的累计保留差额（F04） | 开发修复后由Codex回归；开发 → Codex | [arithmetic.json](../../reports/qa/ISOP-2092/20260926-data-analysis/arithmetic.json) |
| **C07-05 普通投注、有效投注、派彩源单全量对账** | **待核验** / 已执行（Codex） | 按真实纳入范围核对源记录，不重复体育数据 | 体育64笔中63笔与主表重叠；去重候选仍有09-15/22/25差额，09-25投注差14045（D04） | 开发给出Doris纳入/去重/历史修订规则，Codex逐差额复算；开发/产品 → Codex | [source-bets-sport-authoritative.json](../../reports/qa/ISOP-2092/20260926-data-analysis/source-bets-sport-authoritative.json)、[sport-overlap.tsv](../../reports/qa/ISOP-2092/20260926-data-analysis/sport-overlap.tsv) |
| **C07-06 总派彩不依赖net_amount的独立验算** | **未执行** / 未执行（—） | 普通、FS、JP均按独立派彩来源重算 | 已有候选使用net_amount，不能满足用户指定的独立派彩验收 | 开发提供派彩源字段/映射后Codex重新核算；开发 → Codex | 无该项执行证据 |

<a id="c08"></a>
## C08：充提差、投充比与源单

| 测试点 | 结果 / 执行 | 预期 | 实际结果 | 下一步 / 由谁处理 | 证据 |
| --- | --- | --- | --- | --- | --- |
| **C08-01 首页充提差公式** | **通过** / 已执行（Codex） | 充值减提现等于充提差 | 三组区间及日数据可重算；不等于提现源单已对平 | 无需你重复执行；后续版本按需回归；Codex | [arithmetic.json](../../reports/qa/ISOP-2092/20260926-data-analysis/arithmetic.json)、[ui-periods.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-periods.json) |
| **C08-02 首页投充比公式** | **通过** / 已执行（Codex） | 有效投注/充值×100 | 三组区间为1441.68%、1351.49%、1368.83%，与重算一致 | 无需你重复执行；后续版本按需回归；Codex | [arithmetic.json](../../reports/qa/ISOP-2092/20260926-data-analysis/arithmetic.json) |
| **C08-03 明细投充比分子** | **失败** / 已执行（Codex） | 应使用有效投注，和首页一致 | 09-25明细4230.08%，首页4067.83%；明细用了总投注；另3日也复现（F07，关联C04） | 开发修复后由Codex回归；开发 → Codex | [presentation-differences.json](../../reports/qa/ISOP-2092/20260926-data-analysis/presentation-differences.json)、[ratio-focused.png](../../reports/qa/ISOP-2092/20260926-data-analysis/ratio-focused.png) |
| **C08-04 月图投充比聚合** | **失败** / 已执行（Codex） | 先累计有效投注与充值，再计算比率 | 8月图97.84436079354838%，应1284.315205…%；前端使用每日比率平均（F10，关联C04） | 开发修复后由Codex回归；开发 → Codex | [ui-derived-chart.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-derived-chart.json)、[arithmetic.json](../../reports/qa/ISOP-2092/20260926-data-analysis/arithmetic.json) |
| **C08-05 零分母行为** | **待核验** / 已执行（Codex） | 零分母输出需有明确规则 | basic为0、detail为空串、UI为0.00；已查到行为但未确认零分母应0还是--；零值格式失败见C01 | 产品确认零分母规则后Codex补断言；不重复统计C01零值失败；开发/产品 → Codex | [presentation-differences.json](../../reports/qa/ISOP-2092/20260926-data-analysis/presentation-differences.json)、[ui-focused.json](../../reports/qa/ISOP-2092/20260926-data-analysis/ui-focused.json) |
| **C08-06 提现完成金额源单对账** | **待核验** / 已执行（Codex） | 提现统计可追溯到纳入的完成订单 | 总计1814，部分日300/977/348能对应；全量按当前源表完成状态及创建时间不能对平（D03） | 开发提供统计事件/同步与历史状态规则，Codex复算；开发/产品 → Codex | [withdraws-mismatches.json](../../reports/qa/ISOP-2092/20260926-data-analysis/withdraws-mismatches.json)、[withdraws.tsv](../../reports/qa/ISOP-2092/20260926-data-analysis/withdraws.tsv) |
| **C08-07 舍入边界及底层余额快照** | **待核验** / 已执行（Codex） | 精度规则明确且期末快照完整 | 已区分原值精度和真正比率差异；未证明所有舍入边界与Doris快照完整性 | 开发/产品补精度及快照依据，Codex补边界样本；开发/产品 → Codex | [presentation-differences.json](../../reports/qa/ISOP-2092/20260926-data-analysis/presentation-differences.json)、[api-comparison.json](../../reports/qa/ISOP-2092/20260926-data-analysis/api-comparison.json) |

## 未执行项交接

| 测试点 | 下一执行方 | 待执行操作 / 前置 |
| --- | --- | --- |
| C01-05 按TLSQ布局附件做人工视觉验收 | 用户（可选人工验收） | 可选人工验收：打开批准附件，对照首页与弹窗；记录差异截图。不是要求你重跑数据测试 |
| C02-04 周一当天点击本周/上周 | Codex | Codex补受控时钟场景，或09-28当天复测；不要求你手动等待 |
| C02-05 月初当天点击本月/上月 | Codex | Codex补月初/跨年时钟场景；不需要你重复当前日期六快捷项 |
| C04-12 周图各类指标聚合值 | Codex | Codex补周图数值核算；人均分母规则需先明确 |
| C04-20 导出ty=3与三种文件内容 | Codex | Codex在导出任务恢复后补跑、下载和核文件 |
| C05-04 A/B/C隔离人群及首充/复充人数 | Codex | Codex优先找可追溯历史样本，不足再用已授权P0准备受控样本 |
| C06-07 历史登录/投注人数独立去重 | 开发 → Codex | 开发提供事件/去重口径后Codex核算 |
| C07-06 总派彩不依赖net_amount的独立验算 | 开发 → Codex | 开发提供派彩源字段/映射后Codex重新核算 |

执行这些剩余项目后，应补实际结果、证据、执行人和执行时间；未取得新证据前保留未执行。本批未取得精确部署SHA，来源机器基线仍UNREVIEWED；MySQL仅用于源数据核算，不冒充Doris统计结果。
