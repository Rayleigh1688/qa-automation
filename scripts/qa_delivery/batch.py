"""Explicit, finite inbox scan and execution; never starts a listener."""
import json
import sqlite3
import time
from contextlib import closing
from datetime import datetime, timezone
from types import SimpleNamespace
from .connectors import Jira, submit_one
from .pipeline import run_pipeline


def scan_pending(store, telegram, config, max_pages=20):
    """Drain at most max_pages immediately available pages (no long polling)."""
    if not 1 <= max_pages <= 100:
        raise ValueError('max_pages must be 1..100')
    seen = 0
    for _ in range(max_pages):
        before = store.offset()
        updates = telegram.call('getUpdates', {'offset': before, 'timeout': 0,
                                              'limit': 100, 'allowed_updates': ['message']})
        if not isinstance(updates, list):
            raise ValueError('invalid Telegram update batch')
        for update in sorted(updates, key=lambda u: u['update_id']):
            store.ingest(update, config)
            seen += 1
        if len(updates) < 100:
            return {'updates': seen, 'limit_reached': False}
        if store.offset() <= before:
            raise ValueError('Telegram cursor did not advance')
    return {'updates': seen, 'limit_reached': True}


def deliver_pending(store, telegram, config, sleep=time.sleep):
    # Snapshot prevents an external producer from extending this command indefinitely.
    count = store.db.execute('SELECT count(*) FROM outbox WHERE sent=0').fetchone()[0]
    for _ in range(count):
        if not store.deliver_one(telegram, config):
            break
        sleep(3.1)


def run_batch(store, telegram, config, state, *, max_pages=20, jira_factory=Jira, analyzer=None, since=None, **unused):
    """Scan/resolve/preview only. No tests, outgoing messages or Jira writes."""
    from .intake import resolve_pending, preview
    from .pipeline import write_json
    from .scan_history import checkpoint, select_window, record_scan
    started = datetime.now(timezone.utc).isoformat()
    previous, offset_start = checkpoint(store), store.offset()
    telegram.verify(config)
    scanned = scan_pending(store, telegram, config, max_pages)
    try:
        jira = jira_factory(config['jira'])
    except (KeyError, ValueError):
        jira = None
    select_window(store, since)
    from .intake_ai import analyze_pending
    analysis = analyze_pending(store, config, state, **({'analyzer': analyzer} if analyzer else {}))
    resolve_pending(store, jira)
    result = {**scanned, **preview(store, config), 'analysis': analysis,
              'pending_analysis': store.db.execute('SELECT count(*) FROM intake_messages WHERE analyzed=0').fetchone()[0]}
    state.mkdir(parents=True, exist_ok=True)
    record_scan(store, state, result, started, previous, offset_start, since)
    write_json(state / 'preview.json', result)
    from .preview_report import render_preview
    (state / 'preview.md').write_text(render_preview(result, state), encoding='utf-8')
    return result


def refresh_preview(config, state):
    """Rebuild derived review files from saved evidence; never initialize/mutate Store."""
    from .intake import preview
    from .pipeline import write_json
    from .preview_report import render_preview
    if not (state / 'preview.json').is_file() or not (state / 'queue.sqlite3').is_file():
        raise ValueError('尚无本地扫描记录，请先运行扫描')
    saved = json.loads((state / 'preview.json').read_text(encoding='utf-8'))
    with closing(sqlite3.connect((state / 'queue.sqlite3').resolve().as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute('BEGIN')
        current = preview(SimpleNamespace(db=db), config)
        pending = db.execute('SELECT count(*) FROM intake_messages WHERE analyzed=0').fetchone()[0]
    result = {**saved, **current, 'pending_analysis': pending,
              'preview_refreshed_at': datetime.now(timezone.utc).isoformat()}
    write_json(state / 'preview.json', result)
    (state / 'preview.md').write_text(render_preview(result, state), encoding='utf-8')
    return result


def execute_batch(store, telegram, config, state, job_ids, *, pipeline=run_pipeline, sleep=time.sleep):
    telegram.verify(config)
    for job_id in job_ids:
        row = store.claim(job_id)
        if row:
            report = pipeline(config, row, state / 'runs' / row['id'])
            store.finish(row['id'], report)
    return {'jobs': len(job_ids)}


def submit_approved(store, telegram, config, *, max_pages=20, jira_factory=Jira, sleep=time.sleep):
    telegram.verify(config)
    scan_pending(store, telegram, config, max_pages)
    approved = store.db.execute("SELECT id FROM jobs WHERE status='APPROVED' ORDER BY rowid").fetchall()
    for _ in approved:
        submit_one(store, jira_factory(config['jira']), config)
    deliver_pending(store, telegram, config, sleep)
    return {'approved_batches': len(approved)}
