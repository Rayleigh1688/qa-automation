"""Render the standalone HTML report from recorded and sanitized API evidence."""
from html import escape
import json
from pathlib import Path
from string import Template

from qa_core.case_report import evidence_html
from qa_core.result_language import STATUS_LABELS, TYPES


TEMPLATE_PATH = Path(__file__).with_name('templates') / 'api-report.html'
NO_FULL_BODY = object()
DEPLOYMENT_LABELS = {
    'declared': '声明版本，未远程核验',
    'not_provided': '未提供版本',
    'verified': '已由执行流程核验',
    'incomplete': '版本核验未完成',
}
FIELD_VALUE_LABELS = {
    'null': 'null',
    'empty_string': '空字符串',
    'integer_zero': '整数 0',
    'integer_nonzero': '非零整数',
    'nonempty_string': '非空字符串',
    'boolean': '布尔值',
    'empty_list': '空数组',
    'empty_dict': '空对象',
    'nonempty_list': '非空数组',
    'nonempty_dict': '非空对象',
    'float': '浮点数',
}
OP_LABELS = {
    'eq': '等于', 'type': '类型', 'exists': '存在性', 'count': '数量',
    'nonempty': '非空', 'fields_absent_or': '字段缺失或为空值',
    'rows_have_keys': '每条记录包含字段', 'any_row_matches': '匹配指定记录',
}


def _json_html(value):
    formatted = json.dumps(value, ensure_ascii=False, indent=2)
    return escape(formatted.encode('utf-8', errors='backslashreplace').decode('utf-8'))


def _value_html(value):
    if value == '<missing>':
        return '字段缺失'
    if value == '<redacted>':
        return '已脱敏'
    return _json_html(value)


def _badge(status):
    return f'<span class="badge {escape(status)}">{escape(STATUS_LABELS.get(status, status))}</span>'


def _elapsed(milliseconds):
    return f'{milliseconds:,} ms' if type(milliseconds) is int and milliseconds >= 0 else '—'


def _field_values(counts):
    return '，'.join(f'{FIELD_VALUE_LABELS.get(kind, kind)} × {count}' for kind, count in counts.items())


def _assertion_table(checks):
    rows = []
    for check in checks:
        status = check.get('status', '—')
        op = check.get('op', '')
        expected = check.get('expected', '未记录')
        if op == 'fields_absent_or' and isinstance(expected, dict):
            expected_html = '\n'.join(
                f'{escape(field)}  {", ".join(_value_html(value) for value in values) or "字段缺失"}'
                for field, values in expected.items()
            )
        elif op == 'type' and isinstance(expected, str):
            expected_html = escape(TYPES.get(expected, expected))
        else:
            expected_html = _value_html(expected)
        actual = check.get('actual', '未记录')
        categories = []
        for field, counts in check.get('field_observations', {}).items():
            description = _field_values(counts) or '字段缺失'
            categories.append(f'<small>{escape(field)} · {escape(description)}</small>')
        if not categories:
            shape = []
            if op != 'type' and check.get('actual_type'):
                actual_type = check['actual_type']
                shape.append(TYPES.get(actual_type, actual_type))
            if 'actual_length' in check:
                shape.append(f'长度 {check["actual_length"]}')
            if shape:
                categories.append(f'<small>{escape(" · ".join(shape))}</small>')
        unexpected = check.get('unexpected_fields', [])
        if unexpected:
            categories.append(f'<small>不符合的字段 {escape("、".join(unexpected))}</small>')
        if op == 'type' and isinstance(actual, str) and actual in TYPES:
            actual_html = escape(TYPES[actual])
        else:
            actual_html = '' if actual == '<redacted>' and categories else f'<pre>{_value_html(actual)}</pre>'
        rows.append(
            f'<tr data-check="{escape(status)}"><td><code>{escape(check.get("path", ""))}</code>'
            f'<small>{escape(OP_LABELS.get(op, op))}</small></td>'
            f'<td><pre>{expected_html}</pre></td>'
            f'<td>{actual_html}{"".join(categories)}</td><td>{_badge(status)}</td></tr>'
        )
    if not rows:
        return ''
    return ('<h4 class="assertion-heading">断言对照</h4><div class="assertion-scroll" tabindex="0">'
            '<table aria-label="断言对照"><thead><tr><th scope="col">字段 / 检查</th>'
            '<th scope="col">预期</th><th scope="col">实际</th><th scope="col">结果</th>'
            f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def _response_findings(checks):
    rows = []
    for check in checks:
        if check.get('status') != 'FAIL' or not check.get('field_observations'):
            continue
        for field in check.get('unexpected_fields', []):
            counts = check['field_observations'].get(field, {})
            if counts:
                expected = check.get('expected', {})
                missing = '预期字段缺失 · ' if isinstance(expected, dict) and expected.get(field) == [] else ''
                rows.append(f'<li><code>{escape(field)}</code> · {missing}实际 {escape(_field_values(counts))}</li>')
    if not rows:
        return ''
    return ('<div class="response-findings"><h4>失败字段（完整响应统计）</h4>'
            f'<ul>{"".join(rows)}</ul></div>')


def _response_html(response, full_body=NO_FULL_BODY):
    if not isinstance(response, dict):
        return '<p>该批次没有记录响应预览。</p>'
    notes = []
    status = response.get('decode_status')
    if status and status != 'decoded':
        notes.append({'empty': '响应体为空', 'undecodable': '响应体无法解码',
                      'unavailable': '未取得响应体'}.get(status, str(status)))
    if type(response.get('body_bytes')) is int:
        notes.append(f'{response["body_bytes"]:,} 字节')
    if full_body is NO_FULL_BODY:
        if response.get('redacted'):
            notes.append('部分内容已脱敏')
        if type(response.get('omitted_fields')) is int and response['omitted_fields'] > 0:
            notes.append(f'样本中省略 {response["omitted_fields"]:,} 个其他字段')
        if response.get('truncated'):
            notes.append('预览已截断')
    note_html = f'<p>{escape(" · ".join(notes))}</p>' if notes else ''
    if full_body is not NO_FULL_BODY:
        body = f'<pre>{_json_html(full_body)}</pre>'
    else:
        body = (f'<pre>{_json_html(response["body"])}</pre>'
                if 'body' in response and status in (None, 'decoded') else '')
    return note_html + body or '<p>未取得响应体。</p>'


def _request_label(request):
    return ' '.join(str(request[key]) for key in ('method', 'path') if key in request)


def _step_html(step, request_fallback, full_body):
    request = step.get('request') or {}
    response = step.get('response')
    observation = step.get('observation') or {}
    http = observation.get('http')
    business = observation.get('business_status')
    request_ms = response.get('elapsed_ms') if isinstance(response, dict) else None
    duration = (f'请求耗时 {_elapsed(request_ms)}' if type(request_ms) is int
                else f'步骤耗时 {_elapsed(step.get("elapsed_ms"))}')
    metadata = []
    if type(http) is int:
        metadata.append(f'HTTP {http}')
    if type(business) is bool:
        metadata.append('业务成功' if business else '业务失败')
    metadata.append(duration)
    request_html = (_json_html({key: value for key, value in request.items() if key not in {'redacted', 'truncated'}})
                    if request else escape(request_fallback))
    request_notes = ''.join(
        f'<p>{label}</p>' for flag, label in (('redacted', '部分参数已脱敏'), ('truncated', '参数预览已截断'))
        if request.get(flag)
    )
    checks = step.get('assertions', [])
    response_title = '响应正文' if full_body is not NO_FULL_BODY else '响应预览（已脱敏）'
    return (f'<section class="case-step"><div class="step-heading">'
            f'<h3>{escape(_request_label(request) or step.get("id", "执行步骤"))}</h3>'
            f'{_badge(step.get("status", "—"))}</div>'
            f'<p class="result-meta">{escape(" · ".join(metadata))}</p>'
            f'<div class="exchange"><section><h4>请求</h4>{request_notes}<pre>{request_html}</pre></section>'
            f'<section>{_response_findings(checks)}<h4>{response_title}</h4>'
            f'{_response_html(response, full_body)}</section></div>'
            f'{_assertion_table(checks)}</section>')


def _case_html(row, result, folder, response_bodies):
    status = row['执行结果']
    steps = result.get('steps', [])
    request = next((step['request'] for step in steps if step.get('request')), {})
    route = _request_label(request) or row['模块/接口']
    checks = [check for step in steps for check in step.get('assertions', []) if check.get('status') == 'FAIL']
    failure = ''
    conclusion = row['实际结果/失败点']
    if checks:
        fields = [field for check in checks for field in (check.get('unexpected_fields') or [check['path']])]
        failed_fields = '、'.join(dict.fromkeys(fields))
        failure = f'<small class="secondary">{escape(failed_fields)}</small>'
        conclusion = f'{len(checks)} 项断言未通过，涉及 {failed_fields}。'
    expected = row['预期结果']
    if steps and steps[0].get('id'):
        expected = expected.partition('\n' + steps[0]['id'] + ':')[0]
    request_fallback = row['参数/步骤']
    case_id = row['用例编号']
    step_html = ''.join(
        _step_html(step, request_fallback, response_bodies.get((case_id, step.get('id')), NO_FULL_BODY))
        for step in steps
    )
    if not step_html:
        step_html = (f'<div class="exchange"><section><h4>请求</h4><pre>{escape(request_fallback)}</pre></section>'
                     '<section><h4>响应预览（已脱敏）</h4><p>该批次没有记录响应预览。</p></section></div>')
        if row.get('技术断言'):
            step_html += f'<details class="technical"><summary>历史断言记录</summary><pre>{escape(row["技术断言"])}</pre></details>'
    return (f'<details class="case" data-status="{status}"><summary class="list-row">'
            f'<span class="case-label"><span>{escape(row["用例名称"])}'
            f'<small class="case-key">{escape(row["用例编号"])}</small></span></span>'
            f'<span class="route"><code>{escape(route)}</code>{failure}</span>{_badge(status)}'
            f'<span class="elapsed">{_elapsed(result.get("elapsed_ms"))}</span></summary>'
            f'<div class="case-detail"><div class="case-description"><section><h4>用例预期</h4>'
            f'<p>{escape(expected)}</p></section><section><h4>执行结论</h4>'
            f'<p>{escape(conclusion)}</p></section></div>{step_html}'
            f'<p class="evidence">{evidence_html(row["证据"], folder)}</p></div></details>')


def render_api_html(rows, report, summary, folder, *, extra_views, source_time, context, response_bodies=None):
    requirement = report.get('requirement', '')
    title = f'{requirement} API 测试报告' if requirement else 'API 测试报告'
    metadata = [
        ('环境', summary.get('environment')), ('批次', summary.get('run_id')),
        ('执行时间', source_time), ('部署版本', summary.get('deployment')),
    ]
    if 'deployment' in summary:
        metadata.append(('版本核验', DEPLOYMENT_LABELS.get(summary.get('deployment_verification'), '未核验')))
    indexed = {result['id']: result for result in report.get('results', [])}
    bodies = response_bodies or {}
    cases = ''.join(_case_html(row, indexed[row['用例编号']], folder, bodies) for row in rows)
    downloads = '<a href="results.csv">结果 CSV</a>'
    if (Path(folder) / 'result.json').is_file():
        downloads += '<a href="result.json">证据 JSON</a>'
    if extra_views:
        downloads += '<a href="cases.csv">用例 CSV</a><a href="failures.csv">失败清单</a>'
    return Template(TEMPLATE_PATH.read_text(encoding='utf-8')).substitute(
        title=escape(title), context=context, downloads=downloads,
        metadata=''.join(f'<div><dt>{label}</dt><dd>{escape(str(value or "—"))}</dd></div>'
                         for label, value in metadata),
        total=summary['total'], passed=summary['PASS'], failed=summary['FAIL'],
        cases=cases or '<p class="empty">本批没有可展示的接口判定。</p>',
    )
