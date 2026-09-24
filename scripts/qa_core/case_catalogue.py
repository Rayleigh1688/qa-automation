"""Offline, per-story overview and API data views. Never changes executable sources."""
import json
from pathlib import Path
import re
from qa_core.case_report import FIELDS, CATALOGUE_FIELDS, csv_text, validate_cases, project_catalogue
from qa_core.case_design import DESIGN_FIELDS, design_rows, is_card_design
API_FIELDS = ['执行用例编号', '总用例编号', '用例名称', '接口/流程', '前置条件',
              '数据集', '输入变量', '请求/步骤', '预期/断言', '就绪情况']


def catalogue_text(value):
    """Keep link labels readable in CSV without carrying Markdown destinations."""
    return re.sub(r'(?<!!)\[([^\]\n]+)\]\([^\n)]+\)', r'\1', value)


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
        values = [row['Case ID'], kind, story, row['场景'], prerequisite,
                  row['操作步骤'], row['预期结果及副作用检查'], priority.strip(), acceptance.strip()]
        rows.append(dict(zip(FIELDS, map(catalogue_text, values))))
    rows.sort(key=lambda row: row['类型'] == 'API')
    validate_cases(rows)
    return rows


def catalogue_rows(design, story):
    """Design registration states remain metadata, never execution evidence."""
    source = {row['Case ID']: row for row in design}
    rows = []
    for row in overview_rows(design, story):
        item = source[row['用例编号']]
        rows.append({**row, '类型': 'API' if row['类型'] == 'API' else '功能',
                     '状态': item['状态'], '负责人': item['负责人'], '验证方式': item['方式']})
    project_catalogue(rows)
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
    modern = is_card_design(folder / 'test-cases.md')
    catalogue = catalogue_rows(design, story) if modern else overview
    fields = CATALOGUE_FIELDS if modern else FIELDS
    (folder / 'cases.csv').write_text(csv_text(catalogue, fields), encoding='utf-8')
    if data is not None:
        (folder / 'api').mkdir(exist_ok=True)
        (folder / 'api/data-cases.csv').write_text(csv_text(data, API_FIELDS), encoding='utf-8')
    return len(overview), None if data is None else len(data)
