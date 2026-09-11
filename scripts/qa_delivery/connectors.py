"""Small HTTP adapters. No raw remote errors or credentials enter reports."""
import base64
import json
import os
import re
import ssl
import urllib.error
import urllib.request
import uuid
from urllib.parse import urlsplit
from .state import digest


class RemoteError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RemoteError('redirect refused')


def request_json(url, body=None, headers=None, method=None, timeout=35, raw_data=None):
    if urlsplit(url).scheme != 'https':
        raise ValueError('HTTPS required')
    req = urllib.request.Request(url, data=raw_data if raw_data is not None else None if body is None else json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json', **(headers or {})}, method=method)
    try:
        context = ssl.create_default_context(cafile=os.environ.get('QA_CA_BUNDLE') or None)
        with urllib.request.build_opener(NoRedirect, urllib.request.HTTPSHandler(context=context)).open(req, timeout=timeout) as response:
            raw = response.read(4_000_001)
            if len(raw) > 4_000_000:
                raise RemoteError('response too large')
            return json.loads(raw) if raw else {}
    except (urllib.error.URLError, ValueError, TimeoutError, OSError):
        raise RemoteError('remote request failed; response suppressed') from None


class Telegram:
    def __init__(self, token):
        if not re.fullmatch(r'\d+:[A-Za-z0-9_-]+', token):
            raise ValueError('missing or invalid Telegram token')
        self.base = 'https://api.telegram.org/bot' + token

    def call(self, method, body):
        result = request_json(self.base + '/' + method, body)
        if result.get('ok') is not True:
            raise RemoteError('Telegram rejected request')
        return result['result']

    def verify(self, config):
        me = self.call('getMe', {})
        if me.get('username', '').lower() != config['bot_username'].lower():
            raise ValueError('token belongs to a different bot')
        if self.call('getWebhookInfo', {}).get('url'):
            raise ValueError('webhook already active; polling cannot start')
        return me

    def send_document(self, chat_id, text, caption):
        boundary = 'qa-' + uuid.uuid4().hex
        parts = []
        for key, value in {'chat_id': str(chat_id), 'caption': caption, 'parse_mode': 'HTML'}.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="bugs.txt"\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n'.encode())
        parts.append(text.encode('utf-8'))
        parts.append(f'\r\n--{boundary}--\r\n'.encode())
        result = request_json(self.base + '/sendDocument', headers={'Content-Type': 'multipart/form-data; boundary=' + boundary}, raw_data=b''.join(parts))
        if result.get('ok') is not True:
            raise RemoteError('Telegram rejected document')
        return result['result']


class Jira:
    def __init__(self, config):
        self.config = config
        self.base = config['base_url'].rstrip('/')
        parsed = urlsplit(self.base)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.path or parsed.query or parsed.username:
            raise ValueError('invalid Jira base URL')
        email = os.environ[config['email_env']]
        token = os.environ[config['token_env']]
        self.headers = {'Authorization': 'Basic ' + base64.b64encode(f'{email}:{token}'.encode()).decode()}
        if config['relation'] not in ('parent', 'link') or not config['issue_type_id']:
            raise ValueError('explicit Jira issue type and Story relation required')

    def call(self, method, path, body=None):
        return request_json(self.base + '/rest/api/3/' + path, body, self.headers, method)

    def resolve_story(self, key):
        chain = []
        for _ in range(6):
            if not re.fullmatch(r'ISOP-\d+', key) or key in chain:
                raise ValueError('invalid/cyclic Jira parent chain')
            issue = self.call('GET', f'issue/{key}?fields=parent,issuetype,summary')
            if issue.get('key') != key:
                raise ValueError('Jira issue identity mismatch')
            chain.append(key)
            fields = issue['fields']
            if fields['issuetype']['id'] == self.config.get('story_type_id', '10677'):
                return {'story': key, 'chain': chain}
            key = fields.get('parent', {}).get('key', '')
        raise ValueError('no Story in Jira parent chain')

    def find(self, story, fingerprint):
        project = story.split('-')[0]
        result = self.call('POST', 'search/jql', {
            'jql': f'project = "{project}" AND labels = "qa-{fingerprint}"',
            'fields': ['key', 'parent', 'issuelinks'], 'maxResults': 2})
        issues = result.get('issues')
        if not isinstance(issues, list) or len(issues) > 1 or result.get('nextPageToken'):
            raise RemoteError('ambiguous Jira duplicate search')
        return issues[0] if issues else None

    def create(self, payload, bug, fingerprint):
        description = '\n'.join([
            f"Story: {payload['story']} | {payload['environment']} | build {payload['build']}",
            f"Run: {payload['run_id']} | local evidence: reports/telegram/runs/{payload['run_id']}/",
            f"Case: {bug['case_id']} | Basis: {bug['basis']}",
            'Steps: ' + ' → '.join(bug['steps']), 'Expected: ' + bug['expected'],
            'Actual: ' + bug['actual'], 'Evidence: ' + ', '.join(bug['evidence'])])
        fields = {
            'project': {'key': payload['story'].split('-')[0]},
            'issuetype': {'id': self.config['issue_type_id']},
            'summary': bug['title'][:250], 'labels': ['qa-' + fingerprint],
            'description': {'type': 'doc', 'version': 1, 'content': [
                {'type': 'paragraph', 'content': [{'type': 'text', 'text': description}]}]}}
        if self.config['relation'] == 'parent':
            fields['parent'] = {'key': payload['story']}
        result = self.call('POST', 'issue', {'fields': fields})
        if not re.fullmatch(r'[A-Z][A-Z0-9_]*-\d+', result.get('key', '')):
            raise RemoteError('create returned no valid issue key')
        return result['key']

    def link(self, story, key):
        self.call('POST', 'issueLink', {'type': {'name': self.config['link_type']},
                  'inwardIssue': {'key': story}, 'outwardIssue': {'key': key}})

    def ensure_relation(self, story, key):
        issue = self.call('GET', f'issue/{key}?fields=parent,issuelinks')
        fields = issue.get('fields', {})
        if self.config['relation'] == 'parent':
            if fields.get('parent', {}).get('key') != story:
                raise RemoteError('existing issue has a different parent; manual review needed')
            return
        for link in fields.get('issuelinks', []):
            if link.get('type', {}).get('name') == self.config['link_type'] and any(
                link.get(direction, {}).get('key') == story for direction in ('inwardIssue', 'outwardIssue')):
                return
        self.link(story, key)


def submit_one(store, jira, config):
    row = store.db.execute("SELECT * FROM jobs WHERE status='APPROVED' ORDER BY rowid LIMIT 1").fetchone()
    if not row:
        return False
    job = row['id']
    if row['config_hash'] != digest(config):
        with store.db:
            store.db.execute("UPDATE jobs SET status='SUBMIT_BLOCKED' WHERE id=?", (job,))
            store.enqueue_text(f'{job}：配置已改变，提交暂停；重新核对负责人和 Jira 目标。', job)
        return True
    p, report = json.loads(row['payload']), json.loads(row['report'])
    if digest(report)[:16] != row['revision']:
        raise ValueError('review snapshot changed')
    selected = set(json.loads(row['approved']))
    owner = config['stories'].get(p['story'], {}).get('tester_id')
    eligible = {b['id'] for b in report['bugs'] if b['category'] == 'PRODUCT'}
    if not owner or owner != p.get('tester_id') or row['reviewer'] != owner or not selected or not selected <= eligible:
        with store.db:
            store.db.execute("UPDATE jobs SET status='SUBMIT_BLOCKED' WHERE id=?", (job,))
        return True
    completed = []
    with store.db:
        store.db.execute("UPDATE jobs SET status='SUBMITTING' WHERE id=?", (job,))
    try:
        # Validate the parent exists before any creation. Do not create an orphan on typo.
        story = jira.call('GET', f"issue/{p['story']}?fields=issuetype,project")
        if story.get('key') != p['story']:
            raise RemoteError('Story not found')
        for b in report['bugs']:
            if b['id'] not in selected:
                continue
            if b['category'] != 'PRODUCT' or row['reviewer'] != p['tester_id']:
                raise ValueError('invalid approval')
            fp = digest([p['story'], b['case_id'], b['title'], b['expected'], b['actual']])[:32]
            previous = store.db.execute('SELECT * FROM issues WHERE fingerprint=?', (fp,)).fetchone()
            if previous:
                if previous['state'] not in ('DONE', 'CREATED') or not previous['jira_key']:
                    raise RemoteError('earlier submission uncertain; reconcile before retry')
                key = previous['jira_key']
                if previous['state'] == 'CREATED':
                    jira.ensure_relation(p['story'], key)
                    with store.db:
                        store.db.execute("UPDATE issues SET state='DONE',linked=1 WHERE fingerprint=?", (fp,))
            else:
                duplicate = jira.find(p['story'], fp)
                if duplicate:
                    key = duplicate['key']
                    with store.db:
                        store.db.execute('INSERT INTO issues VALUES(?,?,?,?,?,?)', (fp, job, b['id'], 'CREATED', key, 0))
                    jira.ensure_relation(p['story'], key)
                    with store.db:
                        store.db.execute("UPDATE issues SET state='DONE',linked=1 WHERE fingerprint=?", (fp,))
                else:
                    # Commit intent BEFORE POST: a timeout/crash must never cause another create.
                    with store.db:
                        store.db.execute('INSERT INTO issues VALUES(?,?,?,?,?,?)', (fp, job, b['id'], 'INTENT', None, 0))
                    key = jira.create(p, b, fp)
                    with store.db:
                        store.db.execute("UPDATE issues SET state='CREATED',jira_key=? WHERE fingerprint=?", (key, fp))
                    if jira.config['relation'] == 'link':
                        jira.link(p['story'], key)
                    with store.db:
                        store.db.execute("UPDATE issues SET state='DONE',linked=1 WHERE fingerprint=?", (fp,))
            completed.append((key, b['title']))
        with store.db:
            store.db.execute("UPDATE jobs SET status='SUBMITTED' WHERE id=?", (job,))
            text = f"{p['story']} / {p['environment']}：已建立并关联 {len(completed)} 个 BUG\n"
            text += '\n'.join(f'{key} {title}\n{jira.base}/browse/{key}' for key, title in completed)
            store.enqueue_text(text, job, 'bug_summary')
    except (RemoteError, ValueError, KeyError):
        with store.db:
            store.db.execute("UPDATE jobs SET status='SUBMIT_BLOCKED' WHERE id=?", (job,))
            store.enqueue_text(f'{job}：Jira 提交暂停。已成功项已保存；需核对重复问题、关联或不确定响应，禁止整批重试。', job)
    return True
