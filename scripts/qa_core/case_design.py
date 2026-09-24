"""Read human case cards and legacy design tables without executing a plan."""
from pathlib import Path
import re

DESIGN_FIELDS = ['Case ID', '优先级/验收点', '场景', '数据前置', '操作步骤',
                 '预期结果及副作用检查', '方式', '依赖/待确认', '状态', '负责人']
DESIGN_STATUSES = {'PASS', 'FAIL', 'ERROR', 'NOT_RUN', 'BLOCKED', 'OUT_OF_SCOPE'}
CARD_START = '<!-- case-cards:v1 -->'
CARD_END = '<!-- /case-cards -->'
INDEX_FIELDS = ['编号', '用例名称', '状态', '负责人']
LINK_FIELDS = ['编号', '优先级/验收点', '方式']
CARD_FIELDS = {'前置条件': '数据前置', '操作步骤': '操作步骤',
               '预期结果': '预期结果及副作用检查', '待确认': '依赖/待确认'}
ANCHOR_PATTERN = r'\s*<a\s+id=(["\x27])([^"\x27]+)\1\s*></a>\s*'


def verification_kind(value):
    """Keep catalogue layers separate from the existing API/UI/FLOW kinds."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError('missing verification method')
    api, ui = 'API' in value, 'UI' in value
    if not api and not ui:
        raise ValueError('verification method must identify API or UI')
    return 'FLOW' if api and ui else 'UI' if ui else 'API'


def design_paths(path):
    path = Path(path)
    paths = [path]
    api = path.parent / 'api/test-cases.md'
    if path.name == 'test-cases.md' and path.parent.name != 'api' and api.is_file():
        paths.append(api)
    return paths


def has_cards(text):
    return '<!-- case-cards:' in text or CARD_END in text


def is_card_design(path):
    return any(has_cards(p.read_text(encoding='utf-8')) for p in design_paths(path))


def _cells(line):
    if not line.strip().startswith('|'):
        return None
    return [s.strip().replace('\\|', '|')
            for s in re.split(r'(?<!\\)\|', line.strip()[1:-1])]


def _separator(cells):
    return cells and all(re.fullmatch(r':?-+:?', c) for c in cells)


def _owned_id(value, story, *, cards=False):
    pattern = re.escape(story) + r'-C\d+'
    if not cards:
        pattern += r'|R\d+'
    if not re.fullmatch(pattern, value):
        raise ValueError('design case must belong to this story')


def _legacy_rows(text, story):
    rows, active = [], False
    for line in text.splitlines():
        cells = _cells(line)
        if cells is None:
            if active:
                break
            continue
        if cells == DESIGN_FIELDS:
            if active:
                raise ValueError('duplicate design table')
            active = True
            continue
        if not active or _separator(cells):
            continue
        if len(cells) != len(DESIGN_FIELDS):
            raise ValueError('malformed design row')
        row = dict(zip(DESIGN_FIELDS, cells))
        _owned_id(row['Case ID'], story)
        rows.append(row)
    return rows


def _card_table(text, fields):
    rows, active, found = [], False, False
    for line in text.splitlines():
        cells = _cells(line)
        if cells == fields:
            if found:
                raise ValueError('duplicate case-card table')
            active = found = True
            continue
        if cells is None:
            active = False
            continue
        if not active or _separator(cells):
            continue
        if len(cells) != len(fields) or any(not c for c in cells):
            raise ValueError('malformed case-card table row')
        rows.append(dict(zip(fields, cells)))
    if not rows or len({r['编号'] for r in rows}) != len(rows):
        raise ValueError('missing/duplicate case-card table entries')
    return {r['编号']: r for r in rows}


def _card_values(text):
    values, active = {}, None
    for line in text.splitlines():
        if re.match(r'^#{1,2}\s', line) or _cells(line) == LINK_FIELDS:
            break
        if re.fullmatch(r'\s*<a\s+id=["\'][^"\']+["\']\s*></a>\s*', line):
            continue
        match = re.match(r'^\*\*([^*：]+)：\*\*\s*(.*)$', line)
        if match:
            name, content = match.groups()
            if name not in CARD_FIELDS and name != '场景':
                raise ValueError('unknown case-card field: ' + name)
            if name in values:
                raise ValueError('duplicate case-card field: ' + name)
            values[name], active = [content], name
        elif active:
            values[active].append(line)
        elif line.strip():
            raise ValueError('case-card text must use a named field')
    result = {name: '\n'.join(lines).strip() for name, lines in values.items()}
    if any(not result.get(name) for name in CARD_FIELDS):
        raise ValueError('missing case-card field')
    return result


def _card_rows(text, story):
    if text.count(CARD_START) != 1 or text.count(CARD_END) != 1 or text.count('<!-- case-cards:') != 1:
        raise ValueError('case cards need one supported, closed block')
    start, end = text.index(CARD_START), text.index(CARD_END)
    if start >= end:
        raise ValueError('case-card markers out of order')
    block = text[start + len(CARD_START):end]
    if '<!-- case-cards:' in block:
        raise ValueError('nested case-card block')
    index = _card_table(block, INDEX_FIELDS)
    links = _card_table(block, LINK_FIELDS)
    headings = list(re.finditer(r'^###\s+(.+)$', block, re.M))
    anchors = [match.group(2) for line in block.splitlines()
               if (match := re.fullmatch(ANCHOR_PATTERN, line))]
    rows = []
    for pos, heading in enumerate(headings):
        title = re.fullmatch(r'([^\s：]+)：(.+)', heading.group(1).strip())
        if not title:
            raise ValueError('invalid case-card heading')
        key, name = title.group(1), title.group(2).strip()
        _owned_id(key, story, cards=True)
        preceding = block[:heading.start()].rstrip().splitlines()
        anchor = re.fullmatch(ANCHOR_PATTERN, preceding[-1]) if preceding else None
        if not anchor or anchor.group(2) != key.rsplit('-', 1)[-1].lower():
            raise ValueError('case-card heading needs its matching anchor')
        if key not in index or key not in links:
            raise ValueError('case-card index/link entry missing')
        item, link = index[key], links[key]
        label = re.fullmatch(r'\[([^\]]+)\]\(#([A-Za-z0-9_-]+)\)', item['用例名称'])
        if not name or not label or label.group(1) != name or label.group(2) != key.rsplit('-', 1)[-1].lower():
            raise ValueError('case-card index name/anchor differs from heading')
        if item['状态'] not in DESIGN_STATUSES or not item['负责人'].strip():
            raise ValueError('invalid case-card state/owner')
        priority, separator, acceptance = link['优先级/验收点'].partition('/')
        if not priority.strip() or not separator or not acceptance.strip():
            raise ValueError('design needs priority and acceptance reference')
        verification_kind(link['方式'])
        next_start = headings[pos + 1].start() if pos + 1 < len(headings) else len(block)
        values = _card_values(block[heading.end():next_start])
        rows.append({'Case ID': key, '场景': name, '优先级/验收点': link['优先级/验收点'],
                     '方式': link['方式'], '状态': item['状态'], '负责人': item['负责人'],
                     **{target: values[source] for source, target in CARD_FIELDS.items()}})
    keys = {row['Case ID'] for row in rows}
    if not rows or len(keys) != len(rows) or keys != set(index) or keys != set(links):
        raise ValueError('case-card headings/index/links differ or contain duplicate cases')
    if len(anchors) != len(rows) or set(anchors) != {key.rsplit('-', 1)[-1].lower() for key in keys}:
        raise ValueError('missing/duplicate case-card anchors')
    return rows


def _rows(text, story):
    rows = _card_rows(text, story) if has_cards(text) else _legacy_rows(text, story)
    if not rows or len({r['Case ID'] for r in rows}) != len(rows):
        raise ValueError('missing/duplicate design cases')
    return rows


def design_rows(path, story):
    """Aggregate the main functional design and optional sibling API design."""
    rows = []
    for source in design_paths(path):
        rows.extend(_rows(source.read_text(encoding='utf-8'), story))
    if len({r['Case ID'] for r in rows}) != len(rows):
        raise ValueError('duplicate design cases across functional/API files')
    return rows


def design_case_ids(path, story):
    """Strict new designs, with legacy ID-only tables accepted by old consumers."""
    known = set()
    for source in design_paths(path):
        text = source.read_text(encoding='utf-8')
        if has_cards(text) or any(_cells(line) == DESIGN_FIELDS for line in text.splitlines()):
            ids = {r['Case ID'] for r in _rows(text, story)}
        else:
            ids = set(re.findall(r'\|\s*((?:ISOP-\d+-)?[CR]\d+)\s*\|', text))
            if any(key.startswith('ISOP-') and not key.startswith(story + '-') for key in ids):
                raise ValueError('design case must belong to this story')
        if known & ids:
            raise ValueError('duplicate design cases across functional/API files')
        known.update(ids)
    if not known:
        raise ValueError('no acceptance cases found')
    return known
