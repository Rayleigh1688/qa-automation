"""Offline, per-story overview and API data views. Never changes executable sources."""
import json
from pathlib import Path
import re

from qa_core.case_report import FIELDS, csv_text, validate_cases

DESIGN_FIELDS = ['Case ID', '优先级/验收点', '场景', '数据前置', '操作步骤',
                 '预期结果及副作用检查', '方式', '依赖/待确认', '状态', '负责人']
API_FIELDS = ['执行用例编号', '总用例编号', '用例名称', '接口/流程', '前置条件',
              '数据集', '输入变量', '请求/步骤', '预期/断言', '就绪情况']


def design_rows(path, story):
    """Read the established design table, not execution-history or mapping tables."""
    rows, active = [], False
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if not line.startswith('|'):
            if active:
                break
            continue
        cells = [s.strip().replace('\\|', '|') for s in re.split(r'(?<!\\)\|', line.strip()[1:-1])]
        if cells == DESIGN_FIELDS:
            if active:
                raise ValueError('duplicate design table')
            active = True
            continue
        if not active or all(re.fullmatch(r':?-+:?', c) for c in cells):
            continue
        if len(cells) != len(DESIGN_FIELDS):
            raise ValueError('malformed design row')
        row = dict(zip(DESIGN_FIELDS, cells))
        if not re.fullmatch(r'(?:' + re.escape(story) + r'-C\d+|R\d+)', row['Case ID']):
            raise ValueError('design case must belong to this story')
        rows.append(row)
    if not rows or len({r['Case ID'] for r in rows}) != len(rows):
        raise ValueError('missing/duplicate design cases')
    return rows


def overview_rows(design, story):
    rows = []
    for row in design:
        priority, separator, acceptance = row['优先级/验收点'].partition('/')
        if not separator or not acceptance.strip():
            raise ValueError('design needs priority and acceptance reference')
        # FLOW represents a business case spanning API and UI; assignment stays in the design.
        kind = 'FLOW' if 'API' in row['方式'] and 'UI' in row['方式'] else 'UI' if 'UI' in row['方式'] else 'API'
        prerequisite = row['数据前置']
        if row['状态'] == 'OUT_OF_SCOPE':
            prerequisite = '已移出本需求测试范围；' + prerequisite
        if row['依赖/待确认'] not in {'', '—', '-'}:
            prerequisite += '；依赖：' + row['依赖/待确认']
        rows.append(dict(zip(FIELDS, [row['Case ID'], kind, story, row['场景'], prerequisite,
                                     row['操作步骤'], row['预期结果及副作用检查'], priority.strip(), acceptance.strip()])))
    validate_cases(rows)
    return rows


def linked_ids(refs, story, known):
    ids = [ref.strip() if ref.strip() in known or ref.strip().startswith(story + '-') else story + '-' + ref.strip() for ref in refs]
    if not ids or len(ids) != len(set(ids)) or not set(ids) <= known:
        raise ValueError('execution case has missing/unknown/duplicate overview references')
    return ','.join(ids)


def json_text(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def plan_api_rows(plan, cases, known):
    datasets = {case['id'] + ':' + name: name for case in plan['cases'] for name in case.get('datasets', [])}
    rows = []
    for case in cases:
        review = case['review']
        refs = linked_ids(review['验收点'].split(','), plan['requirement'], known)
        if case.get('delivery', {}).get('mode') == 'manual' or review['类型'] == 'UI' or any(s['action'] == 'ui' for s in case.get('steps', [])):
            continue
        rows.append(dict(zip(API_FIELDS, [case['id'], refs, review['用例名称'], review['模块/接口'],
            review['前置条件'], datasets.get(case['id'], '固定组合'), json_text(case.get('variables', {})),
            review['参数/步骤'], review['预期结果'], '可执行' if case.get('steps') else case.get('blocked', '未实现') ])))
    return rows


def legacy_api_rows(suite, known):
    rows = []
    for case in suite['cases']:
        request = case.get('request', {})
        refs = linked_ids(case['case_ids'], suite['requirement'], known)
        rows.append(dict(zip(API_FIELDS, [case['id'], refs, case.get('title', case['id']),
            request.get('path', '业务前置'), case.get('blocked') or '指定环境；按auth配置建立本轮会话',
            '固定组合', json_text({'auth': case.get('auth', 'valid'), 'requires_rows': case.get('requires_rows', False)}),
            json_text(request) if request else '待补执行资产',
            json_text({'expect': case.get('expect'), 'checks': case.get('checks', [])}),
            case.get('blocked') or ('可执行' if request else '未实现') ])))
    return rows


def export_catalogues(folder, *, plan=None, cases=None, suite=None):
    folder = Path(folder)
    story = folder.name
    design = design_rows(folder / 'test-cases.md', story)
    overview = overview_rows(design, story)
    known = {row['用例编号'] for row in overview}
    if plan is not None:
        data = plan_api_rows(plan, cases, known)
    elif suite is not None:
        data = legacy_api_rows(suite, known)
    else:
        data = None
    # Finish validation before replacing either generated view.
    if data is not None and len({r['执行用例编号'] for r in data}) != len(data):
        raise ValueError('duplicate API execution ID')
    (folder / 'cases.csv').write_text(csv_text(overview, FIELDS), encoding='utf-8')
    if data is not None:
        (folder / 'api').mkdir(exist_ok=True)
        (folder / 'api/data-cases.csv').write_text(csv_text(data, API_FIELDS), encoding='utf-8')
    return len(overview), None if data is None else len(data)
