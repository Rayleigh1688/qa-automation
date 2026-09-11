"""Scan checkpoints and bounded daily summaries; Telegram offset remains authoritative."""
from datetime import datetime, timezone
import json
from .pipeline import write_json


def parse_since(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            raise ValueError('timezone required')
        return int(dt.timestamp())
    except ValueError:
        raise ValueError('--since requires ISO time with timezone, e.g. 2026-09-10T15:00:00+08:00') from None


def select_window(store, since):
    if since is None:
        return
    with store.db:
        for row in store.db.execute('SELECT * FROM intake_messages WHERE analyzed IN (0,2)').fetchall():
            date = json.loads(row['payload']).get('date')
            # Unknown timestamps stay pending rather than silently disappearing.
            included = date is None or date >= since
            store.db.execute('UPDATE intake_messages SET analyzed=? WHERE update_id=?', (0 if included else 2, row['update_id']))


def checkpoint(store):
    row = store.db.execute("SELECT value FROM meta WHERE key='last_scan'").fetchone()
    return json.loads(row[0]) if row else None


def record_scan(store, state, result, started, previous, offset_start, since):
    finished = datetime.now(timezone.utc).isoformat()
    timing = {'previous_scan': previous, 'started_at': started, 'finished_at': finished,
              'since': since, 'offset_start': offset_start, 'offset_end': store.offset()}
    result['scan'] = timing
    folder = state / 'scans'; folder.mkdir(parents=True, exist_ok=True)
    path = folder / (datetime.now().astimezone().date().isoformat() + '.json')
    daily = json.loads(path.read_text()) if path.exists() else {'scan_count': 0, 'updates_total': 0, 'first_scan': started}
    daily.update(scan_count=daily['scan_count'] + 1, updates_total=daily['updates_total'] + result['updates'], latest=result)
    write_json(path, daily)
    with store.db:
        store.db.execute("INSERT OR REPLACE INTO meta VALUES('last_scan',?)", (json.dumps({'finished_at': finished, 'offset': store.offset()}),))
