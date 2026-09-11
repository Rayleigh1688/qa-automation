"""Offline end-to-end message/approval/delivery tests; no real integrations."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from support import ROOT
from qa_delivery.state import Store, digest, validate_config
from qa_delivery.pipeline import validate_plan, validate_triage, run_pipeline
from qa_delivery.connectors import RemoteError, submit_one


def config():
    return dict(bot_username='TestBot', submission_chat_id=-10, testing_chat_id=-20,
                submitter_ids=[1], testers={'qa': {'telegram_id': 2}},
                stories={'ISOP-2037': {'tester_id': 2, 'environments': ['FAT'], 'ui': {}}},
                environments={'FAT': {'env_file': '.env.fat', 'version_probes': []}}, jira={})


def report():
    return {'status': 'FAIL', 'summary': 'One observed failure',
            'results': [{'id': 'API:Q1', 'status': 'FAIL', 'detail': 'Mismatch', 'evidence': ['api.json']}],
            'bugs': [{'id': 'B1', 'case_id': 'API:Q1', 'category': 'PRODUCT', 'title': 'Known column missing',
                      'basis': 'AC-01', 'steps': ['Open report', 'Query known sample'],
                      'expected': 'Required field present', 'actual': 'Required field absent', 'evidence': ['api.json']}]}


class TelegramFake:
    def __init__(self): self.sent = []
    def call(self, method, body): self.sent.append((method, body)); return {'message_id': len(self.sent)}
    def send_document(self, chat_id, text, caption): return self.call('sendDocument', {'chat_id': chat_id, 'document': text, 'caption': caption})


class JiraFake:
    base = 'https://test.atlassian.net'
    config = {'relation': 'link'}
    def __init__(self, fail=None, duplicate=None):
        self.fail, self.duplicate, self.creates, self.links = fail, duplicate, [], []
    def call(self, *args): return {'key': 'ISOP-2037'}
    def find(self, *args): return self.duplicate
    def create(self, p, bug, fp):
        self.creates.append(fp)
        if self.fail == 'create': raise RemoteError('lost response')
        return 'ISOP-9999'
    def link(self, story, key):
        self.links.append((story, key))
        if self.fail == 'link': raise RemoteError('link failed')
    def ensure_relation(self, story, key): self.link(story, key)


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'queue.sqlite3'
        self.store, self.config, self.counter = Store(self.path), config(), 0
    def tearDown(self):
        self.store.close(); self.temp.cleanup()
    def message(self, text, user=1, chat=-10, **extra):
        self.counter += 1
        update = {'update_id': self.counter, 'message': {'text': text, 'from': {'id': user}, 'chat': {'id': chat}, **extra}}
        self.store.ingest(update, self.config)
        return update
    def enqueue(self):
        with self.store.db:
            payload = dict(story='ISOP-2037', environment='FAT', build='v1', scopes=['api', 'ui'],
                           round=1, tester_id=self.config['stories']['ISOP-2037']['tester_id'])
            key = digest(payload)[:16]
            payload.update(run_id=key, submitter_id=1)
            self.store.db.execute('INSERT OR IGNORE INTO jobs(id,dedup,payload,status,config_hash) VALUES(?,?,?,?,?)',
                                  (key, key, json.dumps(payload), 'QUEUED', digest(self.config)))
        return self.store.db.execute('SELECT * FROM jobs').fetchone()['id']
    def deliver(self):
        fake = TelegramFake()
        while self.store.deliver_one(fake, self.config): pass
        return fake
    def reviewed(self):
        job = self.enqueue()
        self.store.claim()
        rev = self.store.finish(job, report())
        self.deliver()
        self.message(f'/approve@TestBot {job} {rev} B1', user=2, chat=-20)
        return job

    def test_durable_dedup_and_group_separation(self):
        job = self.enqueue()
        self.message('/test@TestBot ISOP-2037 env=FAT build=v1 scope=ui,api')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM jobs').fetchone()[0], 1)
        self.store.close(); self.store = Store(self.path)
        self.assertEqual(self.store.get(job)['status'], 'QUEUED')
        sent = self.deliver().sent
        self.assertEqual(sent, [])

    def test_ignores_unauthorized_groups_users_bots_and_wrong_bot(self):
        cmd = '/test@TestBot ISOP-2037 env=FAT build=v1 scope=api'
        self.message(cmd, user=9)
        self.message(cmd, chat=-20)
        self.message(cmd.replace('@TestBot', '@OtherBot'))
        self.message(cmd, sender_chat={'id': -10})
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM jobs').fetchone()[0], 0)

    def test_rejects_shell_injection_and_unknown_options(self):
        for bad in ['build=$(id)', 'build=../test', 'build=v1 command=rm', 'build=v1 env=UAT', 'build=v1 round=0']:
            self.message('/test ISOP-2037 env=FAT scope=api ' + bad)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM jobs').fetchone()[0], 0)

    def test_local_review_approval_requires_owner_and_current_revision(self):
        job = self.enqueue(); rev = self.store.finish(job, report())
        self.assertEqual(self.deliver().sent, [])
        self.message(f'/approve {job} {rev} B1', user=3, chat=-20)
        self.message(f'/approve {job} old B1', user=2, chat=-20)
        self.message(f'/approve {job} {rev} all', user=2, chat=-20)
        self.message(f'/approve {job} {rev} B1', user=2, chat=-10)
        self.assertEqual(self.store.get(job)['status'], 'REVIEW')
        self.message(f'/approve {job} {rev} B1', user=2, chat=-20)
        self.assertEqual(self.store.get(job)['status'], 'APPROVED')

    def test_revision_change_invalidates_old_approval(self):
        job = self.enqueue(); old = self.store.finish(job, report()); self.deliver()
        changed = report(); changed['bugs'][0]['title'] = 'Revised title'
        new = self.store.finish(job, changed); self.deliver()
        self.assertNotEqual(old, new)
        self.message(f'/approve {job} {old} B1', user=2, chat=-20)
        self.assertEqual(self.store.get(job)['status'], 'REVIEW')

    def test_nonproduct_cannot_be_approved(self):
        job = self.enqueue(); r = report(); r['bugs'][0]['category'] = 'SCRIPT'
        rev = self.store.finish(job, r); self.deliver()
        self.message(f'/approve {job} {rev} B1', user=2, chat=-20)
        self.assertEqual(self.store.get(job)['status'], 'REVIEW')

    def test_jira_writes_only_after_approval_and_no_second_submission(self):
        fake = JiraFake()
        self.assertFalse(submit_one(self.store, fake, self.config))
        job = self.reviewed()
        self.assertTrue(submit_one(self.store, fake, self.config))
        self.assertEqual(self.store.get(job)['status'], 'SUBMITTED')
        self.assertEqual(fake.links, [('ISOP-2037', 'ISOP-9999')])
        self.assertFalse(submit_one(self.store, fake, self.config))
        self.assertEqual(len(fake.creates), 1)

    def test_lost_create_response_and_link_failure_never_recreate(self):
        for failure, state in [('create', 'INTENT'), ('link', 'CREATED')]:
            with self.subTest(failure=failure):
                self.store.db.execute('DELETE FROM jobs'); self.store.db.execute('DELETE FROM issues'); self.store.db.commit()
                job = self.reviewed(); fake = JiraFake(failure)
                submit_one(self.store, fake, self.config)
                self.assertEqual(self.store.get(job)['status'], 'SUBMIT_BLOCKED')
                self.assertEqual(self.store.db.execute('SELECT state FROM issues').fetchone()[0], state)
                self.assertFalse(submit_one(self.store, fake, self.config))
                self.assertEqual(len(fake.creates), 1)

    def test_jira_dedup_finds_existing_without_create(self):
        job = self.reviewed(); fake = JiraFake(duplicate={'key': 'ISOP-9999'})
        submit_one(self.store, fake, self.config)
        self.assertEqual(fake.creates, [])
        self.assertEqual(self.store.get(job)['status'], 'SUBMITTED')

    def test_restart_marks_running_interrupted_without_replay(self):
        job = self.enqueue(); self.store.claim(); self.store.interrupted()
        self.assertEqual(self.store.get(job)['status'], 'INTERRUPTED')
        self.assertIsNone(self.store.claim())

    def test_config_change_blocks_submission(self):
        job = self.reviewed(); c = copy.deepcopy(self.config); c['testing_chat_id'] = -99
        fake = JiraFake(); submit_one(self.store, fake, c)
        self.assertEqual(fake.creates, [])
        self.assertEqual(self.store.get(job)['status'], 'SUBMIT_BLOCKED')

    def test_outbox_failure_keeps_one_completed_summary(self):
        job = self.reviewed(); submit_one(self.store, JiraFake(), self.config)
        with patch.object(TelegramFake, 'call', side_effect=RemoteError('network')):
            with self.assertRaises(RemoteError): self.store.deliver_one(TelegramFake(), self.config)
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM outbox WHERE sent=0").fetchone()[0], 1)
        sent = self.deliver().sent
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0][1]['chat_id'], -20)
        self.assertIn('ISOP-9999', sent[0][1]['text'])
        self.assertEqual(self.deliver().sent, [])

    def test_whoami_status_and_claim_never_send_or_change_story_owner(self):
        job = self.enqueue()
        for command in ['/whoami@TestBot', '/claim ' + job, '/status ' + job]:
            self.message(command, user=3, chat=-20)
        self.assertEqual(json.loads(self.store.get(job)['payload'])['tester_id'], 2)
        self.assertEqual(self.deliver().sent, [])

    def test_legacy_unsent_messages_are_preserved_but_suppressed(self):
        with self.store.db:
            self.store.db.execute("INSERT INTO outbox(kind,body,sent) VALUES('review','old long report',0)")
        self.store.close(); self.store = Store(self.path)
        self.assertEqual(self.deliver().sent, [])
        self.assertEqual(self.store.db.execute("SELECT sent FROM outbox WHERE body='old long report'").fetchone()[0], 2)

    def test_partial_batch_failure_sends_nothing_and_resume_sends_once(self):
        job = self.enqueue(); r = report(); second = copy.deepcopy(r['bugs'][0]); second.update(id='B2', title='Second defect'); r['bugs'].append(second)
        rev = self.store.finish(job, r)
        self.message(f'/approve {job} {rev} B1,B2', user=2, chat=-20)
        class LaterFailure(JiraFake):
            def link(inner, story, key):
                super().link(story, key)
                if len(inner.links) == 2: raise RemoteError('second link failed')
        fake = LaterFailure(); submit_one(self.store, fake, self.config)
        self.assertEqual(self.store.get(job)['status'], 'SUBMIT_BLOCKED')
        self.assertEqual(self.deliver().sent, [])
        with self.store.db: self.store.db.execute("UPDATE jobs SET status='APPROVED' WHERE id=?", (job,))
        resumed = JiraFake(); submit_one(self.store, resumed, self.config)
        self.assertEqual(resumed.creates, [])
        self.assertEqual(len(self.deliver().sent), 1)

    def test_large_completed_summary_is_one_document_not_message_fragments(self):
        job = self.reviewed(); submit_one(self.store, JiraFake(), self.config)
        with self.store.db:
            self.store.db.execute("UPDATE outbox SET body=? WHERE kind='bug_summary'", ('<script>' * 1000,))
        sent = self.deliver().sent
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0][0], 'sendDocument')
        self.assertEqual(sent[0][1]['document'], '<script>' * 1000)

    def test_missing_version_is_explicitly_unverified(self):
        from qa_delivery.pipeline import check_version
        with patch('qa_delivery.pipeline.request_json') as request:
            self.assertFalse(check_version({}, '未提供'))
            request.assert_not_called()
        with patch('qa_delivery.pipeline.request_json', return_value={'version':'v2'}):
            with self.assertRaises(ValueError):
                check_version({'version_probes':[{'url':'https://example.test','field':'version'}]}, 'v1')

    def test_same_group_config_is_rejected(self):
        c = self.config; c['testing_chat_id'] = c['submission_chat_id']
        with self.assertRaises(ValueError): validate_config(c)

    def test_ai_cannot_invent_evidence_or_bug_on_pass(self):
        r = report()
        validate_triage(r, r['results'])
        r['bugs'][0]['evidence'] = ['old-run.json']
        with self.assertRaises(ValueError): validate_triage(r, r['results'])
        r = report(); r['results'][0]['status'] = 'PASS'
        with self.assertRaises(ValueError): validate_triage(r, r['results'])

    def test_ui_plan_requires_independent_basis_known_target_and_assertion(self):
        scan = {'pages': {'list': {'elements': [{'id': 'E1'}]}}}
        plan = {'cases': [{'id': 'U1', 'case_id': 'C01', 'basis': 'AC01', 'page': 'list', 'blocked': '',
                          'steps': [{'op': 'assert_visible', 'target': 'E1', 'value': ''}]}]}
        validate_plan(plan, scan, {'C01'}, {'requests': []})
        for op, target in [('click', 'E1'), ('assert_visible', 'E99'), ('eval', 'E1')]:
            changed = copy.deepcopy(plan); changed['cases'][0]['steps'][0].update(op=op, target=target)
            with self.assertRaises(ValueError): validate_plan(changed, scan, {'C01'}, {'requests': []})


class AccountGuardTests(unittest.TestCase):
    def test_wrong_business_account_stops_before_login(self):
        from qa_delivery.pipeline import check_account
        with patch('qa_delivery.pipeline.load_environment', return_value={'ADMIN_EMAIL': 'other@example.test'}):
            with self.assertRaisesRegex(ValueError, 'business login'):
                check_account({'account_email': 'qa@example.test'}, {'env_file': '.env.fat'})
        with patch('qa_delivery.pipeline.load_environment', return_value={'ADMIN_EMAIL': 'QA@example.test'}):
            check_account({'account_email': 'qa@example.test'}, {'env_file': '.env.fat'})


class JsonRedactionTests(unittest.TestCase):
    def test_timestamp_remains_numeric_and_secret_quotes_cannot_break_json(self):
        from qa_delivery.pipeline import redact_value
        value = {'date': 1789026720, 'message_id': 8380, 'reply': None,
                 'text': 'call 12345678901 or qa@example.test', 'nested': ['secret"value']}
        with patch.dict('os.environ', {'TEST_TOKEN': 'secret"value'}):
            clean = json.loads(json.dumps(redact_value(value)))
        self.assertEqual(clean['date'], value['date'])
        self.assertEqual(clean['message_id'], 8380)
        self.assertIsNone(clean['reply'])
        self.assertEqual(clean['nested'], ['[REDACTED]'])
        self.assertNotIn('12345678901', clean['text'])
        self.assertNotIn('qa@example.test', clean['text'])
