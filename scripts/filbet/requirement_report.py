"""Simple business steps for the explicitly selected 2027 normal regression."""
import copy


# Only reviewed no-match scenarios qualify; a null result for a positive query must fail.
EMPTY_QUERY_IDS = {f'2027-API-{n:03}' for n in (30,33,34,35,37,39,40,42)}
EMPTY_EXPLANATION = '通过（按用户确认的新规则复评，未重新请求）：不匹配查询返回null，总数为0，HTTP/业务成功，查询前后快照不变。null和[]都表示查无数据；原始旧断言保留供追溯。'


def assessment_status(item):
    if item.get('status') != 'FAIL' or item.get('id') not in EMPTY_QUERY_IDS:
        return item['status']
    steps = item.get('steps', [])
    failures = [c for step in steps for c in step.get('assertions', []) if c.get('status') == 'FAIL']
    query = next((step for step in steps if step.get('id') == 'filter'), {})
    no_effects = next((step for step in steps if step.get('id') == 'query-no-effects'), {})
    if (query.get('observation') == {'http':200,'business_status':True}
        and no_effects.get('status') == 'PASS'
        and any(c.get('path') == 'body.data.t' and c.get('op') == 'eq' and c.get('status') == 'PASS' for c in query.get('assertions', []))
        and failures and all(c.get('path') == 'body.data.d' and c.get('op') == 'pluck_set'
                             and c.get('actual_type') == 'NoneType' for c in failures)
        and all(step.get('status') == 'PASS' for step in steps if step.get('id') != 'filter')
        and all(x.get('status') == 'PASS' for x in item.get('recovery', []))):
        return 'REASSESSED_PASS'
    return item['status']


def display_report(report):
    """One reviewed status for every public view; preserve raw execution evidence."""
    result = copy.deepcopy(report)
    for item in result.get('results', []):
        if assessment_status(item) == 'REASSESSED_PASS':
            item['status'] = 'PASS'
            item['actual'] = EMPTY_EXPLANATION
            item['category'] = '通过（规则复评；原始断言FAIL，未重跑）'
    return result


def write_reviewed_views(folder, cases, report, *, extra_views=False):
    from pathlib import Path
    from qa_core.case_report import write_views
    summary = write_views(folder, cases, display_report(report), extra_views=extra_views)
    count = sum(assessment_status(x) == 'REASSESSED_PASS' for x in report.get('results', []))
    if count:
        page = Path(folder)/'results.html'
        note = ('<p style="padding:16px;background:#edf3f8">本页与评审报告采用同一结论：'
                + str(count) + '项不命中查询按已确认规则复评通过，未重新请求。'
                + '<a href="assessment.html">评审报告</a> · <a href="result.json">原始执行证据（含旧断言）</a></p>')
        page.write_text(page.read_text().replace('<h1>测试结果</h1>', '<h1>测试结果</h1>'+note, 1))
    return summary


def display_cases(cases, profile, environment):
    rows = copy.deepcopy(cases)
    for row in rows:
        description = profile.get('cases', {}).get(row['用例编号'])
        if not description:
            continue
        row['前置条件'] = environment + '；A为超级管理员，B为Codex。使用本轮专用会员，具体准备以执行结果为准。'
        row['参数/步骤'] = description
        row['预期结果'] = '按上述业务步骤完成；关键请求成功，资料/申请状态与该操作一致。详细断言见本批result.json。'
    return rows


def write_assessment(folder, cases, report, profile):
    from collections import Counter
    from html import escape
    from pathlib import Path
    from qa_core.case_report import display_time
    folder = Path(folder)
    lookup = {c['用例编号']:c for c in cases}
    counts = Counter(assessment_status(x) for x in report['results'])
    raw_counts = Counter(x['status'] for x in report['results'])
    labels = {'PASS':'通过','FAIL':'失败','REASSESSED_PASS':'通过（规则复评）','NOT_RUN':'未执行','ERROR':'准备/执行错误'}
    csv_rows = []
    rows = []
    for item in report['results']:
        case = lookup[item['id']]
        status = assessment_status(item)
        actual = '已完成本项业务核对。' if item['status']=='PASS' else item.get('actual','')
        explanations = {
            '2027-API-001':'重复编辑请求返回成功，预期拒绝重复提交。',
            '2027-API-003':'未实际修改资料的编辑请求返回成功，预期拒绝；需结合字段变化确认。',
            '2027-API-015':'并发编辑未满足唯一成功/状态变更/审计一致性断言；详见技术检查。',
            '2027-API-018':'夹带只读字段的请求返回成功，未满足拒绝预期；不能仅据此断定只读字段已被修改。',
        }
        if item['status']=='FAIL' and item['id'] in explanations and not item.get('source_description'):
            actual = explanations[item['id']]
        if status == 'REASSESSED_PASS':
            actual = EMPTY_EXPLANATION
        elif item.get('failed_step'):
            actual = '未满足检查的步骤：' + item['failed_step'] + '。' + actual
        if item['id']=='2027-UI-014' and item['status']!='PASS':
            actual = 'Restore还原操作未完成；请展开技术详情查看具体失败位置。'
        steps = profile.get('cases',{}).get(item['id'],case['参数/步骤'])
        csv_rows.append({'用例编号':item['id'],'检查内容':case['用例名称'],'报告结论':labels[status],'说明':actual,'操作':steps,'原始断言状态':item['status']})
        details = '<p>'+escape(actual)+'</p><details><summary>步骤与结果</summary><p>'+escape(steps)+'</p><p>'+escape(actual)+'</p><details><summary>技术详情</summary><pre>'+escape(__import__('json').dumps(item.get('steps',[]),ensure_ascii=False,indent=2))+'</pre></details></details>'
        rows.append('<tr><td>'+escape(item['id'])+'</td><td>'+escape(case['用例名称'])+'</td><td>'+labels[status]+'</td><td>'+details+'</td></tr>')
    totals = str(counts['PASS']+counts['REASSESSED_PASS'])+'通过'
    if counts['REASSESSED_PASS']: totals += '（含'+str(counts['REASSESSED_PASS'])+'项规则复评）'
    totals += '、'+'、'.join(str(counts[s])+labels[s] for s in ('FAIL','NOT_RUN','ERROR'))
    import csv, json
    with (folder/'assessment.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        fields = ['用例编号','检查内容','报告结论','说明','操作','原始断言状态']
        writer = csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for row in csv_rows:
            writer.writerow({k:("'"+v if v.startswith(('=','+','-','@','\t','\r')) else v) for k,v in row.items()})
    notes_path = folder/'assessment-context.json'
    context = json.loads(notes_path.read_text()) if notes_path.exists() else {}
    notes = ''.join('<p>'+escape(x)+'</p>' for x in context.get('notes',[]))
    for link in context.get('links',[]):
        target = Path(link['path'])
        if target.is_absolute() or '..' in target.parts or not (folder/target).is_file():
            raise ValueError('assessment link must be an existing local report file')
        notes += '<p><a href="'+escape(link['path'],quote=True)+'">'+escape(link['label'])+'</a></p>'
    raw_summary = '、'.join(str(raw_counts[k])+labels[k] for k in ('PASS','FAIL','NOT_RUN','ERROR'))
    explanation = '<p>规则已按用户确认更新：不命中查询接受null或[]，总数必须为0；HTTP/业务成功及无副作用检查保留。匹配查询仍须返回预期记录。本报告中“规则复评”依据既有执行证据，不是重新实测。</p><details><summary>原始技术断言计数（未修改）</summary><p>'+escape(raw_summary)+'</p><p>旧断言FAIL留作追溯；仅符合新规则且证据完整的空结果按通过复评，未执行和其他错误不改判。</p></details>' if counts['REASSESSED_PASS'] else ''
    provenance = report.get('source_selection','本批实测，不合并历史通过结果。')
    scope = profile.get('description', '执行范围见冻结计划。')
    if report.get('role_preconditions',{}).get('missing_permissions'):
        scope += ' 当前Codex角色缺少复核列表/复核授权；相关5项前置阻塞，未通过改权制造通过。'
    deferred = profile.get('deferred', [])
    deferred_html = '<h2>本轮暂略过（'+str(len(deferred))+'项）</h2><details><summary>逐项查看范围及原因</summary><ul>' + ''.join('<li>'+escape(x['id']+' '+x['name']+'：'+x['reason'])+'</li>' for x in deferred) + '</ul></details>' if deferred else ''
    content = '<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>ISOP-2027 '+escape(report['environment'])+'回归测试</title><style>body{max-width:1200px;margin:30px auto;padding:0 20px;font:15px/1.65 system-ui;color:#243044}table{border-collapse:collapse;width:100%}td,th{padding:10px;border:1px solid #ddd;text-align:left;vertical-align:top}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}a{color:#175caa}.summary{padding:16px;background:#edf3f8}</style><h1>ISOP-2027 '+escape(report['environment'])+'回归测试</h1><p>'+escape(display_time(report['source_time']))+'</p><p class="summary">'+str(len(rows))+'项：'+totals+'</p>'+explanation+notes+'<p>'+escape(scope)+' A为超级管理员，B为Codex。</p><p>'+escape(provenance)+'</p><p><a href="assessment.csv">下载评审CSV</a> · <a href="results.html">用例明细</a> · <a href="results.csv">明细CSV</a> · <a href="result.json">原始执行证据（旧断言）</a></p><table><tr><th>编号</th><th>检查内容</th><th>结果</th><th>操作说明</th></tr>'+''.join(rows)+'</table>'+deferred_html+'</html>'
    (folder/'assessment.html').write_text(content)
