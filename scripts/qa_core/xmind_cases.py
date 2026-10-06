"""Exchange human case definitions and recorded evidence with Xmind, offline."""
import copy
import csv
import io
import re
import uuid

from qa_core.case_report import FIELDS, csv_text, join_results, validate_cases

RESULT_BRANCH = '本批执行结果'
ALIASES = {
    '用例编号': '用例编号', 'Case ID': '用例编号', 'ID': '用例编号',
    '用例名称': '用例名称', '名称': '用例名称',
    '类型': '类型', '验证方式': '类型',
    '模块/接口': '模块/接口', '模块': '模块/接口', '接口': '模块/接口',
    '前置条件': '前置条件', '前置': '前置条件', '数据前置': '前置条件',
    '参数/步骤': '参数/步骤', '操作步骤': '参数/步骤', '步骤': '参数/步骤',
    '预期结果': '预期结果', '预期': '预期结果',
    '级别': '级别', '优先级': '级别',
    '验收点': '验收点', '需求点': '验收点', '测试数据': '测试数据',
}


def topic(title, children=()):
    value = {'id': uuid.uuid4().hex, 'class': 'topic', 'title': title}
    if children:
        value['children'] = {'attached': list(children)}
    return value


def field_topic(key, value):
    return topic(key, [topic(value)])


def children(node):
    """Floating topics are included; summary/relationship labels are not cases."""
    groups = node.get('children', {})
    return [child for group in ('attached', 'detached', 'floating') for child in groups.get(group, [])]


def _all_children(node):
    """Managed result topics may have been moved to any relationship group."""
    return [child for nodes in node.get('children', {}).values() for child in nodes]


def _field(title):
    key, separator, inline = re.split(r'([：:])', title, maxsplit=1) if re.search(r'[：:]', title) else (title, '', '')
    canonical = ALIASES.get(key.strip())
    return canonical, inline.strip() if separator else ''


def _lines(node, level=0):
    lines = ['  ' * level + node.get('title', '')]
    note = node.get('notes', {}).get('plain', {}).get('content', '')
    if note:
        lines.extend('  ' * (level + 1) + line for line in note.split('\n'))
    for child in children(node):
        lines.extend(_lines(child, level + 1))
    return lines


def _value(node, inline):
    parts = [value for value in (inline, node.get('notes', {}).get('plain', {}).get('content', '')) if value]
    if children(node):
        parts.append('\n'.join(line for child in children(node) for line in _lines(child)))
    return '\n'.join(parts)


def _identity(title):
    match = re.fullmatch(r'\[([A-Za-z0-9_.:-]+)\]\s*(?:[：:|]\s*)?(.*)', title, re.S)
    if match:
        return match.group(1), match.group(2).strip()
    match = re.fullmatch(r'([A-Za-z][A-Za-z0-9_.:-]*)\s+(.*)', title, re.S)
    if match and re.search(r'\d', match.group(1)):
        return match.group(1), match.group(2).strip()
    return None


def _has_case_descendant(node):
    for child in children(node):
        fields = [_field(item.get('title', ''))[0] for item in children(child)]
        identity = _identity(child.get('title', ''))
        if '用例编号' in fields or (identity is not None and (
                child.get('title', '').startswith('[')
                or any(key in {'前置条件', '参数/步骤', '预期结果'} for key in fields))):
            return True
        if _has_case_descendant(child):
            return True
    return False


def _case(node, path):
    identity = _identity(node.get('title', ''))
    fields = [(_field(child.get('title', '')), child) for child in children(node)]
    explicit_id = any(key == '用例编号' for (key, _), _child in fields)
    # Bare alphanumeric headings such as "W26 测试用例" or "P0 回归"
    # are also normal module titles. Require a case field to disambiguate
    # them. A bracketed heading with descendant cases but no case fields is
    # a group too; explicit ID fields always identify a case.
    has_case_fields = any(key in {'前置条件', '参数/步骤', '预期结果'} for (key, _), _child in fields)
    bare_group = identity is not None and not node.get('title', '').startswith('[') and not has_case_fields
    nested_group = identity is not None and not has_case_fields and _has_case_descendant(node)
    if not explicit_id and (identity is None or bare_group or nested_group):
        return None
    values = {}
    for (key, inline), child in fields:
        if key:
            if key in values:
                raise ValueError('duplicate Xmind case field: ' + key)
            values[key] = _value(child, inline)
    key, name = identity or (values['用例编号'].strip(), node.get('title', '').strip())
    if '用例编号' in values and values['用例编号'].strip() != key:
        raise ValueError('Xmind case title and explicit ID differ')
    name = values.get('用例名称', name)
    kind = values.get('类型', 'UI').strip()
    kind = {'人工UI': 'UI', '功能': 'UI', 'API+UI': 'FLOW', 'API/UI': 'FLOW'}.get(kind, kind)
    steps = values.get('参数/步骤', '')
    if values.get('测试数据', '').strip():
        steps = '测试数据：' + values['测试数据'] + '\n操作步骤：' + steps
    row = {
        '用例编号': key, '类型': kind, '模块/接口': values.get('模块/接口', ' / '.join(path)),
        '用例名称': name, '前置条件': values.get('前置条件', ''),
        '参数/步骤': steps, '预期结果': values.get('预期结果', ''),
        '级别': values.get('级别', '中'), '验收点': values.get('验收点', '未关联'),
    }
    # Data alone is not an operation, even though it is shown in the steps cell.
    if not values.get('参数/步骤', '').strip():
        raise ValueError('Xmind case needs explicit steps')
    validate_cases([row])
    return row


def extract_cases(document):
    cases, locations = [], []

    def walk(node, sheet, path):
        if node.get('title') == RESULT_BRANCH:
            return
        row = _case(node, path)
        if row is not None:
            cases.append(row)
            locations.append({'case_id': row['用例编号'], 'sheet_id': sheet['id'], 'topic_id': node['id']})
            return
        for child in children(node):
            walk(child, sheet, path + [node.get('title', '')])

    for sheet in document.sheets:
        walk(sheet['rootTopic'], sheet, [])
    validate_cases(cases)
    return cases, locations


def cases_to_sheets(cases, title='测试用例'):
    validate_cases(cases)
    groups = {}
    for row in cases:
        fields = [field_topic(key, row[key]) for key in FIELDS if key not in {'用例编号', '用例名称'}]
        groups.setdefault(row['模块/接口'], []).append(topic('[' + row['用例编号'] + '] ' + row['用例名称'], fields))
    root = topic(title, [topic(module, nodes) for module, nodes in groups.items()])
    root['structureClass'] = 'org.xmind.ui.logic.right'
    return [{'id': uuid.uuid4().hex, 'class': 'sheet', 'title': title, 'rootTopic': root}]


def template_sheets(title='测试用例模板'):
    rows = []
    for number, name, steps, expected in [
        (1, '正常查询（请替换示例）', '打开指定列表，选择已确认的日期并查询', '目标记录出现，关键字段与已确认数据一致'),
        (2, '精确筛选（请替换示例）', '输入目标记录的完整账号并查询', '仅返回匹配记录，清空筛选后恢复列表'),
    ]:
        rows.append(dict(zip(FIELDS, [f'TC-{number:03}', 'UI', '示例模块 / 列表查询', name,
            '已具备测试权限与专用样本；请替换为真实前置', steps, expected, '中', '未关联'])))
    sheets = cases_to_sheets(rows, title)
    sheets[0]['rootTopic']['notes'] = {'plain': {'content': '示例用例尚未执行。请人工确认前置、步骤和预期，保留唯一编号；不要填写凭据或未脱敏个人资料。'}}
    for case in sheets[0]['rootTopic']['children']['attached'][0]['children']['attached']:
        case['children']['attached'].insert(3, field_topic('测试数据', '请填写脱敏样本别名与日期区间'))
    return sheets


def fill_results(document, report, *, cases=None):
    definitions, locations = extract_cases(document)
    if cases is not None:
        validate_cases(cases)
        frozen = {c['用例编号']: c for c in cases}
        if {c['用例编号']: c for c in definitions} != frozen:
            # Imported CSV is protected against spreadsheet formulas. Compare
            # its exact canonical encoding rather than stripping arbitrary
            # apostrophes from the user's original text.
            csv_cases = csv.DictReader(io.StringIO(csv_text(definitions, FIELDS).removeprefix('\ufeff')))
            if {c['用例编号']: c for c in csv_cases} != frozen:
                raise ValueError('Xmind case definitions differ from the frozen cases')
    if not isinstance(report, dict) or not isinstance(report.get('results'), list):
        raise ValueError('result JSON needs a results list')
    if any(not isinstance(r, dict) or not isinstance(r.get('id'), str) or
           not isinstance(r.get('status'), str) or not isinstance(r.get('actual', ''), str) or
           not isinstance(r.get('evidence', ''), str) or not isinstance(r.get('category', ''), str)
           for r in report['results']):
        raise ValueError('malformed Xmind result record')
    if any(r['status'] != 'NOT_RUN' and not r.get('evidence', '').strip() for r in report['results']):
        raise ValueError('Xmind result evidence must not be blank')
    rows = join_results(definitions, {'results': report['results']})
    sheets = copy.deepcopy(document.sheets)
    indexed = {}

    def index(node):
        indexed[node['id']] = node
        for child in _all_children(node):
            index(child)

    for sheet in sheets:
        index(sheet['rootTopic'])
    managed = ['执行结果', '实际结果', '分类', '证据', '来源批次', '环境', '来源时间']
    for row, location in zip(rows, locations):
        node = indexed[location['topic_id']]
        attached = node.setdefault('children', {}).setdefault('attached', [])
        branches = [c for c in _all_children(node) if c.get('title') == RESULT_BRANCH]
        if len(branches) > 1:
            raise ValueError('duplicate Xmind result branch')
        branch = branches[0] if branches else topic(RESULT_BRANCH)
        values = [row['执行结果'], row['实际结果/失败点'], row['分类'] or '未指定', row['证据'] or '无',
                  str(report.get('run_id', '未提供')), str(report.get('environment', '未提供')),
                  str(report.get('source_time', '未提供'))]
        branch_children = branch.setdefault('children', {}).setdefault('attached', [])
        for key, value in zip(managed, values):
            matches = [c for c in _all_children(branch) if re.split(r'[：:]', c.get('title', ''), maxsplit=1)[0].strip() == key]
            if len(matches) > 1:
                raise ValueError('duplicate Xmind result field')
            if not matches:
                branch_children.append(field_topic(key, value))
            else:
                field = matches[0]
                notes = field.get('notes', {})
                if notes.get('plain', {}).get('content', '') or any(v for k, v in notes.items() if k != 'plain'):
                    raise ValueError('result field notes are ambiguous; review the map before filling')
                leaves = _all_children(field)
                if not leaves:
                    field.setdefault('children', {}).setdefault('attached', []).append(topic(value))
                elif len(leaves) != 1 or _all_children(leaves[0]):
                    raise ValueError('result field must have one value topic')
                else:
                    notes = leaves[0].get('notes', {})
                    if notes.get('plain', {}).get('content', '') or any(v for k, v in notes.items() if k != 'plain'):
                        raise ValueError('result field value notes are ambiguous; review the map before filling')
                    leaves[0]['title'] = value
                field['title'] = key
        if not branches:
            attached.append(branch)
    return sheets
