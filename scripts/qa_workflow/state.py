"""Append-only evidence and independent manual revisions, backed by SQLite."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from qa_delivery.state import digest
from qa_core.execution_plan import expand
from qa_core.team_delivery import mode


def now():
    return datetime.now(timezone.utc).isoformat()


class State:
    def __init__(self, root, directory=None):
        self.root = Path(root).resolve()
        self.directory = Path(directory or self.root/'reports/workflow').resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.directory/'state.sqlite3', timeout=15)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS events (
            seq INTEGER PRIMARY KEY, event_key TEXT UNIQUE NOT NULL,
            story TEXT NOT NULL, kind TEXT NOT NULL, created TEXT NOT NULL, payload TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS triggers (
            event_key TEXT PRIMARY KEY, status TEXT NOT NULL, payload TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, payload TEXT NOT NULL);
        ''')
        self.db.commit()

    def close(self):
        self.db.close()

    def append(self, story, kind, payload, key=None):
        key = key or digest([story, kind, payload])
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO events(event_key,story,kind,created,payload) VALUES(?,?,?,?,?)',
                            (key, story, kind, now(), json.dumps(payload, ensure_ascii=False)))
        return key

    def meta(self, key, value=None):
        if value is not None:
            with self.db:
                self.db.execute('INSERT OR REPLACE INTO metadata VALUES(?,?)', (key, json.dumps(value)))
            return value
        row = self.db.execute('SELECT payload FROM metadata WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def seed(self):
        return json.loads((self.root/'requirements/status-seed.json').read_text(encoding='utf-8'))

    def view(self):
        rows = {r['story']: {**r, 'history': [], 'manual': {}, 'automatic': [], 'workflow': []} for r in self.seed()}
        for event in self.db.execute('SELECT * FROM events ORDER BY seq'):
            if event['story'] not in rows:
                continue
            row = rows[event['story']]
            entry = {'revision': event['seq'], 'kind': event['kind'], 'recorded_at': event['created'], **json.loads(event['payload'])}
            row['history'].append(entry)
            if event['kind'] == 'manual':
                row['manual'][entry['channel']] = entry
            elif event['kind'] == 'automatic':
                row['automatic'].append(entry)
            else:
                row['workflow'].append(entry)
        return {'requirements': list(rows.values()), 'generated_at': now()}

    def manual(self, story, value):
        if story not in {r['story'] for r in self.seed()}:
            raise ValueError('未知需求')
        if value.get('channel') not in ('api', 'ui', 'stage'):
            raise ValueError('未知状态栏目')
        for name in ('status', 'author', 'source', 'reason'):
            if not isinstance(value.get(name), str) or not value[name].strip() or len(value[name]) > 2000:
                raise ValueError('状态、修改人、来源和原因必填且不能超过2000字')
        if type(value.get('base_revision')) is not int:
            raise ValueError('缺少编辑版本')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            prior = self.db.execute("SELECT seq,payload FROM events WHERE story=? AND kind='manual' ORDER BY seq DESC", (story,)).fetchall()
            current = next((r['seq'] for r in prior if json.loads(r['payload'])['channel'] == value['channel']), 0)
            if current != value['base_revision']:
                raise ValueError('状态已被其他窗口修改，请刷新后重试')
            payload = {k: value[k].strip() for k in ('channel','status','author','source','reason')}
            payload['supersedes'] = current
            self.db.execute('INSERT INTO events(event_key,story,kind,created,payload) VALUES(?,?,?,?,?)',
                            (digest([story, payload, now()]), story, 'manual', now(), json.dumps(payload, ensure_ascii=False)))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def claim(self, key, payload):
        # A crashed RUNNING event stays uncertain; never replay writes automatically.
        with self.db:
            result = self.db.execute('INSERT OR IGNORE INTO triggers VALUES(?,?,?)',
                                     (key, 'RUNNING', json.dumps(payload, ensure_ascii=False)))
        return result.rowcount == 1

    def finish(self, key, status):
        with self.db:
            self.db.execute('UPDATE triggers SET status=? WHERE event_key=?', (status, key))


def automatic_evidence(root, path, story):
    report = json.loads(path.read_text(encoding='utf-8'))
    if report.get('mode') != 'execution' or report.get('requirement') != story:
        return None
    # A checkpoint is not a completed run; the runner adds report timing last.
    if 'report' not in report.get('timings_ms',{}): return None
    snapshot = path.parent/'cases.snapshot.json'
    plan_path = path.parent/'plan.snapshot.json'
    if not snapshot.is_file() or not plan_path.is_file(): return None
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    if plan.get('requirement') != story or not report.get('cases_sha256'): return None
    api_ids = {c['id'] for c in expand(plan) if mode(c)=='automatic'
               and c['review']['类型']!='UI' and not any(s['action']=='ui' for s in c.get('steps',[]))}
    results = [r for r in report.get('results', []) if r['id'] in api_ids]
    if not results: return None
    statuses = {r['status'] for r in results}
    if not statuses <= {'PASS','FAIL','ERROR','NOT_RUN'} or len({r['id'] for r in results}) != len(results):
        raise ValueError('invalid automatic result')
    status = 'FAIL' if 'FAIL' in statuses else 'ERROR' if 'ERROR' in statuses else 'NOT_RUN' if statuses != {'PASS'} else 'PASS'
    relative = str(path.relative_to(root))
    return {'status': status, 'source': relative,
        'report': str(path.with_name('results.html').relative_to(root)),
        'sha256': digest(report), 'run_id': report['run_id'], 'time': report.get('source_time',''),
        'environment': report.get('environment'), 'version': report.get('deployment','未提供'),
        'plan_sha256': report.get('cases_sha256'), 'snapshot_sha256':digest(plan),
        'case_ids': [r['id'] for r in results],
        'note': '仅本批API范围；不代表整项验收，历史批次与人工修订独立保留'}


def collect_results(state):
    """Only completed execution reports become automatic evidence; never import manual merges."""
    for seed in state.seed():
        story = seed['story']
        for path in sorted((state.root/'reports/qa'/story).glob('*/result.json')):
            try:
                payload = automatic_evidence(state.root,path,story)
            except (ValueError,OSError,KeyError,TypeError):
                # A concurrently written/incomplete report cannot erase prior imported evidence.
                continue
            if payload:
                state.append(story,'automatic',payload,key=digest([payload['source'],payload['sha256']]))
