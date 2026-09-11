"""Offline case catalogue and concise result views. Never executes tests."""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import csv
from html import escape
import io
import json
from pathlib import Path
import re
from qa_core.result_language import friendly_row, STATUS_LABELS

FIELDS = ['用例编号', '类型', '模块/接口', '用例名称', '前置条件', '参数/步骤', '预期结果', '级别', '验收点']
RESULT_FIELDS = FIELDS + ['执行结果', '实际结果/失败点', '分类', '证据']
STATUSES = ('PASS', 'FAIL', 'NOT_RUN', 'ERROR')


def display_time(value):
    """Display offset-aware timestamps in UTC+8; preserve unknown timezones."""
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, TypeError, AttributeError):
        return value
    if parsed.tzinfo is None:
        return value
    return parsed.astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S') + '（UTC+8）'


def execution_status(item):
    """Adapt legacy runner records without changing the original evidence."""
    status = item['status']
    if status == 'BLOCKED':
        return 'NOT_RUN'
    if status == 'FAIL':
        details = item.get('details', [])
        obs = item.get('observation', {})
        if any('request/evaluation exception' in d for d in details) or (
                obs and type(obs.get('http')) is not int):
            return 'ERROR'
    return status


def load_cases(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != FIELDS:
            raise ValueError('CSV columns must be: ' + ', '.join(FIELDS))
        cases = list(reader)
    validate_cases(cases)
    return cases


def validate_cases(cases):
    seen = set()
    if not cases:
        raise ValueError('empty catalogue')
    for case in cases:
        if set(case) != set(FIELDS) or any(not isinstance(v, str) for v in case.values()):
            raise ValueError('malformed case row')
        key = case['用例编号']
        if not re.fullmatch(r'[A-Za-z0-9_.:-]+', key) or key in seen:
            raise ValueError('invalid or duplicate case ID: ' + key)
        seen.add(key)
        if case['类型'] not in {'API', 'UI', 'FLOW'}:
            raise ValueError('type must be API/UI/FLOW')
        if any(not case[k].strip() for k in FIELDS):
            raise ValueError('incomplete case: ' + key)


def join_results(cases, report):
    validate_cases(cases)
    known = {c['用例编号'] for c in cases}
    indexed = {}
    for item in report.get('results', []):
        key, status = item['id'], item['status']
        if key not in known or key in indexed or status not in STATUSES:
            raise ValueError('unknown/duplicate case or status: ' + key)
        if not str(item.get('actual', '')).strip():
            raise ValueError('actual result or non-execution reason required: ' + key)
        if status != 'NOT_RUN' and not item.get('evidence'):
            raise ValueError('evidence required: ' + key)
        indexed[key] = item
    rows = []
    for case in cases:
        item = indexed.get(case['用例编号'], {'status': 'NOT_RUN', 'actual': '本批次未执行'})
        rows.append({**case, '执行结果': item['status'], '实际结果/失败点': str(item['actual']),
                     '分类': item.get('category', ''), '证据': item.get('evidence', '')})
    if report.get('execution_methods'):
        for row in rows:
            item = indexed.get(row['用例编号'],{})
            row.update({'执行方式':{'manual':'手动','automatic':'自动'}.get(report['execution_methods'].get(row['用例编号']), '未指定'),
                '执行人':item.get('executor',''),'执行时间':display_time(item.get('executed_at',item.get('source_time',''))),
                '来源批次':item.get('source_run_id',report.get('packet_id',''))})
    return rows


def csv_text(rows, fields):
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    # Protect spreadsheet applications from treating user-controlled text as formulas.
    for row in rows:
        writer.writerow({k: ("'" + str(row.get(k, '')) if str(row.get(k, '')).lstrip().startswith(('=', '+', '-', '@'))
                             else row.get(k, '')) for k in fields})
    return '\ufeff' + output.getvalue()


def write_views(folder, cases, report, *, extra_views=True):
    rows = [friendly_row(row) for row in join_results(cases, report)]
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    counts = Counter(r['执行结果'] for r in rows)
    summary = {s: counts[s] for s in STATUSES}
    summary.update(total=len(rows), executed=counts['PASS'] + counts['FAIL'],
                   run_id=report.get('run_id', ''), environment=report.get('environment', ''),
                   source_time=report.get('source_time', ''), mode=report.get('mode', 'execution'))
    if 'deployment' in report:
        summary['deployment'] = report['deployment']
        summary['deployment_verification'] = report.get('deployment_verification',{}).get('status','declared')
    result_fields = RESULT_FIELDS + (['执行方式','执行人','执行时间','来源批次'] if report.get('execution_methods') else [])
    outputs = {'results.csv': csv_text(rows, result_fields),
               'results.html': render_html(rows, summary, folder, extra_views=extra_views)}
    if extra_views:
        outputs.update({'cases.csv': csv_text(cases, FIELDS),
                        'failures.csv': csv_text([r for r in rows if r['执行结果'] == 'FAIL'], result_fields),
                        'pending.csv': csv_text([r for r in rows if r['执行结果'] in {'ERROR', 'NOT_RUN'}], result_fields),
                        'summary.json': json.dumps(summary, ensure_ascii=False, indent=2) + '\n'})
    if any((folder / name).exists() for name in outputs):
        raise ValueError('result views already exist; use a new run directory')
    for name, content in outputs.items():
        (folder / name).write_text(content, encoding='utf-8')
    return summary


def render_html(rows, summary, folder, *, extra_views=True):
    groups = defaultdict(list)
    for row in rows:
        groups[((row.get('执行方式','')+' / ' if row.get('执行方式') else '')+row['类型'], row['模块/接口'])].append(row)
    body = []
    for (kind, module), items in groups.items():
        counts = Counter(r['执行结果'] for r in items)
        label = ' · '.join(f'{STATUS_LABELS[s]} {counts[s]}' for s in STATUSES if counts[s])
        body.append(f'<details class="group" open><summary>{escape(kind)} / {escape(module)} <small>{label}</small></summary>')
        for row in items:
            status = row['执行结果']
            evidence = escape(row['证据'])
            # Only local existing files become links; arbitrary schemes are plain text.
            source = Path(row['证据'])
            if row['证据'] and not re.match(r'^[a-zA-Z]+:', row['证据']) and source.is_file():
                import os
                from urllib.parse import quote
                href = quote(os.path.relpath(source.resolve(), folder.resolve()), safe='/')
                evidence = f'<a href="{escape(href, quote=True)}">查看证据</a>'
            actual = f'<span class="actual">{escape(row["实际结果/失败点"])}</span>' if status != 'PASS' else ''
            body.append(f'<details class="case" data-status="{status}"><summary><b class="{status}">{STATUS_LABELS[status]}</b> '
                        f'{escape(row["用例名称"])}{actual}</summary><dl><dt>用例编号</dt><dd>{escape(row["用例编号"])}</dd>' +
                        ''.join(f'<dt>{key}</dt><dd>{escape(row[key])}</dd>' for key in ['前置条件', '参数/步骤', '预期结果', '实际结果/失败点', '分类']+([k for k in ['执行方式','执行人','执行时间','来源批次'] if k in row])) +
                        f'<dt>证据</dt><dd>{evidence or "—"}</dd></dl>' + ('<details class="technical"><summary>技术断言（供排查）</summary><pre>'+escape(row["技术断言"])+'</pre></details>' if row.get("技术断言") else '') + '</details>')
        body.append('</details>')
    return '''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>测试结果</title><style>
body{font:15px system-ui;margin:32px auto;padding:0 24px;max-width:1100px;background:#f7f8fa;color:#223}
h1{font-size:26px}summary{cursor:pointer;padding:12px}.group{background:white;border:1px solid #ddd;border-radius:8px;margin:14px 0}
.case{border-top:1px solid #eee;margin:0 12px}.case summary{font-size:14px}small{color:#666;margin-left:12px}
b{display:inline-block;min-width:76px}.PASS{color:#147d43}.FAIL{color:#bf2635}.ERROR{color:#9b5100}.NOT_RUN{color:#666}
.actual{display:block;margin:6px 0 0 80px;color:#555}dl{display:grid;grid-template-columns:100px 1fr;gap:10px;padding:0 12px 12px}dt{color:#777}dd{margin:0;white-space:pre-wrap;overflow-wrap:anywhere}
.technical{margin:0 24px 16px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f6f8;padding:12px}input,select{padding:10px;border:1px solid #aaa;border-radius:5px}nav{display:flex;gap:12px;flex-wrap:wrap}.hidden{display:none}
</style><h1>测试结果</h1>''' + f'<p>{escape(summary["run_id"])} · {escape(summary["environment"])} · {escape(display_time(summary["source_time"]))}</p>' + (
        '<p>部署版本：'+escape(str(summary['deployment']))+' · '+escape({'declared':'声明版本，未远程核验','not_provided':'未提供版本','verified':'已由执行流程核验','incomplete':'版本核验未完成'}.get(summary.get('deployment_verification'),'未核验'))+'</p>' if 'deployment' in summary else '') + (
        '<p>历史证据整理，本次未重新测试；仅统计此用例表。</p>' if summary['mode'] == 'historical-summary' else '<p>人工回填与自动证据汇总；来源可能为不同批次，本次导入未执行测试。</p>' if summary['mode']=='evidence-summary' else '<p>执行准备清单，尚未执行测试；人工用例等待回填。</p>' if summary['mode']=='manual-preparation' else '') + \
        '<p>' + '　'.join(f'{STATUS_LABELS[key]} <strong>{summary[key]}</strong>' for key in STATUSES) + \
        f'　总用例 {summary["total"]}（执行错误和未执行不计入已执行）</p>' + '''
<nav><input id="search" aria-label="搜索用例" placeholder="搜索编号、名称、失败点">
<select id="status" aria-label="执行结果"><option value="">全部结果</option><option value="FAIL">失败</option><option value="PASS">通过</option><option value="NOT_RUN">未执行</option><option value="ERROR">执行出错</option></select>
<a href="results.csv">全部结果</a>''' + ('<a href="cases.csv">用例CSV</a><a href="failures.csv">失败清单</a><a href="pending.csv">未执行/执行错误</a>' if extra_views else '') + '</nav>' + ''.join(body) + '''
<script>function filter(){let q=document.getElementById('search').value.toLowerCase(),s=document.getElementById('status').value;
document.querySelectorAll('.case').forEach(e=>e.classList.toggle('hidden',!!((s&&e.dataset.status!==s)||!e.textContent.toLowerCase().includes(q))));
document.querySelectorAll('.group').forEach(e=>e.classList.toggle('hidden',!e.querySelector('.case:not(.hidden)')))}
document.getElementById('search').addEventListener('input',filter);document.getElementById('status').addEventListener('change',filter);</script></html>'''
