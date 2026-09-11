"""Durable queue, immutable review revisions and human-authorized submissions."""
import hashlib
import html
import json
import re
import sqlite3
from pathlib import Path


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def validate_config(c):
    if c['submission_chat_id'] == c['testing_chat_id']:
        raise ValueError('submission and testing groups must differ')
    for field in ('submission_chat_id', 'testing_chat_id'):
        if type(c[field]) is not int or c[field] >= 0:
            raise ValueError('group IDs must be negative integers')
    if not re.fullmatch(r'[A-Za-z0-9_]+bot', c['bot_username'], re.I):
        raise ValueError('invalid bot username')
    testers = {t.get('telegram_id') for t in c.get('testers', {}).values() if t.get('telegram_id')}
    for story, item in c['stories'].items():
        scopes = item.get('test_scopes', ['api', 'ui'])
        if (not isinstance(scopes, list) or not scopes or any(s not in ('api', 'ui') for s in scopes)
                or len(set(scopes)) != len(scopes)):
            raise ValueError('Story test_scopes must be a nonempty unique list of api/ui')
        execution = item.get('execution', {})
        if not isinstance(execution,dict) or set(execution)-{'case_ids','allow_write','insecure'}:
            raise ValueError('invalid Story execution options')
        for key in ('case_ids','allow_write'):
            values = execution.get(key,[])
            if not isinstance(values,list) or any(not isinstance(v,str) or not v.strip() for v in values) or len(set(values))!=len(values):
                raise ValueError('execution selections must be unique strings')
        if type(execution.get('insecure',False)) is not bool:
            raise ValueError('execution insecure must be boolean')
        if not re.fullmatch(r'ISOP-\d+', story):
            raise ValueError('invalid Story')
        if item.get('tester_id') is not None and (type(item['tester_id']) is not int or item['tester_id'] <= 0):
            raise ValueError('tester_id must be a Telegram user ID')
        if item.get('tester_id') is not None and item['tester_id'] not in testers:
            raise ValueError('Story owner must be one configured tester')
        if not item.get('environments') or not set(item['environments']) <= set(c['environments']):
            raise ValueError('Story environment mapping missing')
    return c


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS intake_messages (update_id INTEGER PRIMARY KEY, payload TEXT NOT NULL, analyzed INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS candidates (id TEXT PRIMARY KEY, payload TEXT NOT NULL, status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS jobs (
          id TEXT PRIMARY KEY, dedup TEXT UNIQUE, payload TEXT NOT NULL,
          status TEXT NOT NULL, report TEXT, revision TEXT, approved TEXT,
          reviewer INTEGER, config_hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS outbox (
          id INTEGER PRIMARY KEY, job TEXT, kind TEXT, body TEXT NOT NULL,
          sent INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS issues (
          fingerprint TEXT PRIMARY KEY, job TEXT, bug TEXT, state TEXT,
          jira_key TEXT, linked INTEGER NOT NULL DEFAULT 0);
        ''')
        # Preserve legacy notifications as suppressed local history; never flush them.
        with self.db:
            self.db.execute("UPDATE outbox SET sent=2 WHERE sent=0 AND kind != 'bug_summary'")

    def close(self):
        self.db.close()

    def offset(self):
        row = self.db.execute("SELECT value FROM meta WHERE key='offset'").fetchone()
        return int(row[0]) if row else 0

    def enqueue_text(self, text, job=None, kind='notice'):
        # Only one completed Jira batch is deliverable. Other events stay local.
        self.db.execute('INSERT INTO outbox(job,kind,body,sent) VALUES(?,?,?,?)',
                        (job, kind, text, 0 if kind == 'bug_summary' else 2))

    def ingest(self, update, config):
        uid = update['update_id']
        with self.db:
            if uid < self.offset():
                return
            self.db.execute("INSERT OR REPLACE INTO meta VALUES('offset',?)", (str(uid + 1),))
            m = update.get('message', {})
            if m.get('chat', {}).get('id') == config['submission_chat_id']:
                from .intake_ai import capture
                capture(self, update, config)
                return
            user = m.get('from', {})
            if user.get('is_bot') or m.get('sender_chat') or not user.get('id'):
                return
            text = m.get('text', '')
            words = text.split()
            if not words:
                return
            command = words[0].split('@')
            if len(command) > 2 or (len(command) == 2 and command[1].lower() != config['bot_username'].lower()):
                return
            chat = m.get('chat', {}).get('id')
            if command[0] == '/whoami' and chat == config['testing_chat_id']:
                self.enqueue_text(f"Telegram 用户 ID：{user['id']}；用户名：{user.get('username', '未设置')}。请在本机负责人映射中绑定此数字 ID。")
            elif command[0] == '/approve' and chat == config['testing_chat_id']:
                self._approve(words[1:], user['id'], config)
            elif command[0] == '/status' and chat == config['testing_chat_id'] and len(words) == 2:
                row = self.get(words[1])
                if row:
                    self.enqueue_text(f"{row['id']}：{row['status']}", row['id'])

    def get(self, job):
        return self.db.execute('SELECT * FROM jobs WHERE id=?', (job,)).fetchone()

    def claim(self, job_id=None):
        with self.db:
            row = self.db.execute("SELECT * FROM jobs WHERE status='QUEUED' AND (? IS NULL OR id=?) ORDER BY rowid LIMIT 1",
                                  (job_id, job_id)).fetchone()
            if row:
                self.db.execute("UPDATE jobs SET status='RUNNING' WHERE id=?", (row['id'],))
                self.enqueue_text(f"开始测试 {row['id']}。", row['id'])
            return row

    def interrupted(self):
        with self.db:
            for row in self.db.execute("SELECT id FROM jobs WHERE status IN ('RUNNING','SUBMITTING')").fetchall():
                self.db.execute("UPDATE jobs SET status='INTERRUPTED' WHERE id=?", (row['id'],))
                self.enqueue_text(f"{row['id']} 执行中断，需核对本轮证据；不自动重放测试或 Jira 写入。", row['id'])

    def finish(self, job, report):
        revision = digest(report)[:16]
        with self.db:
            self.db.execute("DELETE FROM outbox WHERE job=? AND kind='review' AND sent=0", (job,))
            self.db.execute("UPDATE jobs SET status='REVIEW',report=?,revision=?,approved=NULL,reviewer=NULL WHERE id=?",
                            (encoded(report), revision, job))
        return revision

    def _approve(self, args, user, config):
        if len(args) != 3:
            return
        job, revision, selected = args
        row = self.get(job)
        if not row:
            return
        p = json.loads(row['payload'])
        if row['config_hash'] != digest(config):
            return
        owner = config['stories'].get(p['story'], {}).get('tester_id')
        if not owner or user != owner or owner != p.get('tester_id'):
            self.enqueue_text(f'{job}：仅分配的测试负责人可以确认。', job)
            return
        if row['status'] != 'REVIEW' or row['revision'] != revision:
            self.enqueue_text(f'{job}：确认未生效，请核对本地报告并使用当前列表版本。', job)
            return
        ids = selected.split(',')
        report = json.loads(row['report'])
        eligible = {b['id'] for b in report['bugs'] if b['category'] == 'PRODUCT'}
        if not ids or len(ids) != len(set(ids)) or not set(ids) <= eligible:
            self.enqueue_text(f'{job}：编号无效，仅可确认 PRODUCT 类候选 BUG。', job)
            return
        self.db.execute("UPDATE jobs SET status='APPROVED',approved=?,reviewer=? WHERE id=?",
                        (encoded(ids), user, job))
        self.enqueue_text(f"{job} 已确认 {','.join(ids)}，等待提交 Jira。", job)

    def deliver_one(self, telegram, config):
        row = self.db.execute("SELECT o.* FROM outbox o JOIN jobs j ON j.id=o.job WHERE o.sent=0 AND o.kind='bug_summary' AND j.status='SUBMITTED' ORDER BY o.id LIMIT 1").fetchone()
        if not row:
            return False
        owner = None
        if row['job']:
            owner = json.loads(self.get(row['job'])['payload']).get('tester_id')
        mention = f'<a href="tg://user?id={owner}">测试负责人</a>' if owner else '待认领'
        text = mention + '\n' + html.escape(row['body'])
        if len(text) <= 3900:
            telegram.call('sendMessage', {'chat_id': config['testing_chat_id'], 'text': text, 'parse_mode': 'HTML'})
        else:
            telegram.send_document(config['testing_chat_id'], row['body'], mention + '\n已建立的完整 BUG 清单')
        with self.db:
            self.db.execute('UPDATE outbox SET sent=1 WHERE id=?', (row['id'],))
        return True
