"""Natural-language submissions are evidence for local review, never execution authority."""
import json
import re
from .state import digest, encoded
from .connectors import RemoteError


def requirement_catalog(root=None):
    """Only existing requirement directories are selectable testing tasks."""
    from .pipeline import ROOT
    root = root or ROOT / 'requirements'
    result = {}
    for path in sorted(root.glob('ISOP-*')):
        if not path.is_dir() or not re.fullmatch(r'ISOP-\d+', path.name):
            continue
        title = path.name
        design = path / 'design.md'
        if design.is_file():
            heading = next((s[2:] for s in design.read_text(encoding='utf-8').splitlines() if s.startswith('# ')), '')
            title = re.sub(r'^' + re.escape(path.name) + r'\s*[：:]?\s*', '', heading)
            title = re.sub(r'\s*[—–]\s*测试设计\s*$', '', title) or path.name
        result[path.name] = title
    return result


def local_story_index(root=None):
    from .pipeline import ROOT
    root = root or ROOT / 'requirements'
    found = {}
    for path in root.glob('ISOP-*/design.md'):
        story = path.parent.name
        found.setdefault(story, set()).add(story)
        for line in path.read_text(encoding='utf-8').splitlines():
            if re.match(r'^\s*-\s*子任[务務][：:]', line):
                for key in set(re.findall(r'\bISOP-\d+\b', line)):
                    found.setdefault(key, set()).add(story)
    # Conflicting documentation is not sufficient evidence for a mapping.
    return {key: next(iter(stories)) for key, stories in found.items() if len(stories) == 1}


def resolve_pending(store, jira):
    index = local_story_index()
    for row in store.db.execute("SELECT * FROM candidates WHERE status='PENDING'").fetchall():
        p = json.loads(row['payload'])
        try:
            if p['issue'] in index:
                p.update(story=index[p['issue']], chain=[p['issue'], index[p['issue']]], resolution='本地design子任务记录；执行前核对Jira')
                with store.db:
                    store.db.execute('UPDATE candidates SET payload=? WHERE id=?', (encoded(p), row['id']))
                continue
            if jira is None:
                raise ValueError('Jira credentials missing')
            resolved = jira.resolve_story(p['issue'])
            p.update(story=resolved['story'], chain=resolved['chain'], resolution='Jira parent关系已核对')
        except (RemoteError, ValueError, KeyError):
            p.update(story=None, resolution='所属Story未核实：检查Jira凭据、权限或工单类型')
        with store.db:
            store.db.execute('UPDATE candidates SET payload=? WHERE id=?', (encoded(p), row['id']))


def preview(store, config):
    rows = [{'id': row['id'], **json.loads(row['payload'])}
            for row in store.db.execute("SELECT * FROM candidates WHERE status='PENDING' ORDER BY rowid")]
    groups = {}
    for p in rows:
        story_config = config['stories'].get(p.get('story'), {})
        p['tester_id'] = story_config.get('tester_id')
        if 'test_scopes' in story_config:
            p['intake_scopes'] = p['scopes']
            p['scopes'] = [s for s in p['scopes'] if s in story_config['test_scopes']]
            p['scope_basis'] = '需求评审限定：' + ','.join(story_config['test_scopes'])
        evidence = [e for e in p.get('evidence', []) if e.get('message_id') == p.get('message_id')]
        own = p.get('text', '') + encoded([e.get('links', []) for e in evidence])
        if not re.search(r'\bISOP-\d+\b', own, re.I):
            continue
        key = (p['story'] or p['issue'], p['environment'], p['build'], tuple(p['scopes']))
        if key not in groups:
            groups[key] = {**p, 'member_ids': [], 'issues': [], 'source_messages': []}
        g = groups[key]
        g['member_ids'].append(p['id'])
        if p['issue'] not in g['issues']:
            g['issues'].append(p['issue'])
        g['source_messages'].append({'message_id': p.get('message_id'), 'text': p['text'],
            'reason': p.get('reason', ''), 'action': p.get('ai_action', 'UNCERTAIN'),
            'scope_note': p.get('scope_note', ''), 'environment_source': p.get('environment_source', '')})
    catalog = requirement_catalog()
    rows, unmatched = [], []
    for row in groups.values():
        if row.get('story') in catalog:
            rows.append({**row, 'requirement_title': catalog[row['story']]})
        else:
            unmatched.append({**row, 'unmatched_reason': '所属需求未核实' if not row.get('story') else '需求目录尚未建立'})
    from .pipeline import ROOT
    from .requirement_bridge import task_plan
    for row in rows:
        if row.get('story') in config['stories']:
            row['execution'] = task_plan(ROOT,config,row)
    return {'revision': digest([rows, config])[:16], 'candidates': rows, 'unmatched': unmatched}


def select_candidates(current, *, requirements=None, candidates=None):
    """Resolve explicit requirement selections without silently widening batches."""
    if bool(requirements) == bool(candidates):
        raise ValueError('请选择 --requirements 或 --candidates 之一')
    values = [value.strip() for value in (requirements or candidates).split(',')]
    if not all(values) or len(values) != len(set(values)):
        raise ValueError('选择不能为空或重复')
    available = current['candidates']
    if candidates:
        if not set(values) <= {row['id'] for row in available}:
            raise ValueError('候选不在当前需求列表中，请重新扫描确认')
        return values
    selected = []
    for story in values:
        matches = [row for row in available if row['story'] == story]
        if not re.fullmatch(r'ISOP-\d+', story) or not matches:
            raise ValueError(story + ' 不在当前待确认需求列表中')
        if len(matches) != 1:
            raise ValueError(story + ' 存在多个环境、版本或范围；请查看preview.json，用 --candidates 明确选择批次')
        selected.append(matches[0]['id'])
    return selected



def confirm(store, config, selected, revision):
    """Local explicit approval binds the entire displayed candidate snapshot/config."""
    from .pipeline import ROOT
    with store.db:
        store.db.execute('BEGIN IMMEDIATE')
        if store.db.execute('SELECT 1 FROM intake_messages WHERE analyzed=0').fetchone():
            raise ValueError('群消息尚未完成AI分析，请重新扫描后确认')
        current = preview(store, config)
        if revision != current['revision'] or not selected or len(selected) != len(set(selected)):
            raise ValueError('候选清单已改变或选择无效，请重新扫描并确认')
        by_id = {p['id']: p for p in current['candidates']}
        prepared = []
        for key in selected:
            p = by_id.get(key)
            if not p or not p['story'] or p['story'] not in config['stories']:
                raise ValueError('所属Story尚未核实或尚未配置')
            if not p['scopes']:
                raise ValueError('消息范围与需求评审范围不相符，请核实提测范围')
            if config.get('pilot_story') and p['story'] != config['pilot_story']:
                raise ValueError('当前试跑仅开放配置的pilot_story')
            if p['environment'] not in config['stories'][p['story']]['environments']:
                raise ValueError('环境尚未开放')
            if not (ROOT / 'requirements' / p['story'] / 'test-cases.md').is_file():
                raise ValueError('缺少需求验收用例')
            if not p.get('tester_id'):
                raise ValueError('请先为Story指定一名固定测试负责人')
            payload = {**p, 'run_id': key, 'round': 1, 'confirmed_preview': revision,
                       'scope_note': '用户确认本批API执行范围及UI人工清单；子任务不会自动代表整Story通过'}
            prepared.append((key, payload))
        for key, p in prepared:
            store.db.execute('INSERT INTO jobs(id,dedup,payload,status,config_hash) VALUES(?,?,?,?,?)',
                             (key, key, encoded(p), 'QUEUED', digest(config)))
            store.db.executemany("UPDATE candidates SET status='CONFIRMED' WHERE id=?", [(member,) for member in p['member_ids']])
            store.enqueue_text(f"已确认测试 {key}：{p['issue']} → {p['story']} / {p['environment']} / 版本{p['build']}；待测试人员认领。", key)
    return [key for key, _ in prepared]
