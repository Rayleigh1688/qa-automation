"""Natural-language scan, verified parent mapping and explicit pre-test approval."""
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from support import ROOT
from qa_delivery.batch import run_batch, execute_batch, submit_approved, scan_pending
from qa_delivery.intake import confirm, preview
from qa_delivery.state import Store
from qa_delivery.connectors import Jira
from test_telegram_delivery import config, report, JiraFake, TelegramFake


class Inbox(TelegramFake):
    def __init__(self, pages):
        super().__init__(); self.pages = list(pages); self.fetches = []
    def verify(self, config): return {'id': 1}
    def call(self, method, body):
        if method == 'getUpdates':
            self.fetches.append(body)
            return self.pages.pop(0) if self.pages else []
        return super().call(method, body)


def msg(n, text, user=999, chat=-10, **extras):
    return {'update_id': n, 'message': {'message_id': n, 'text': text, 'from': {'id': user}, 'chat': {'id': chat}, **extras}}


class Resolver(JiraFake):
    def resolve_story(self, key): return {'story': 'ISOP-2037', 'chain': [key, 'ISOP-2037']}


def fake_analysis(config, folder, phase, instruction, data, schema):
    decisions = []
    for m in data['messages']:
        if m['message_id'] not in data['new_message_ids']:
            continue
        keys = re.findall(r'ISOP-\d+', json.dumps(m))
        decisions.append({'message_id': m['message_id'], 'issue': keys[0] if keys else '',
                          'action': 'READY' if keys else 'IGNORE', 'evidence_ids': [m['message_id']],
                          'reason': '测试夹具的模拟判断', 'scope_note': '接口和页面', 'environment': 'FAT'})
    return {'summary': '模拟AI分析', 'decisions': decisions}


class BatchTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('qa_delivery.intake.local_story_index', return_value={})
        patcher.start(); self.addCleanup(patcher.stop)
        self.temp = tempfile.TemporaryDirectory(); self.state = Path(self.temp.name)
        self.store = Store(self.state / 'queue.sqlite3'); self.c = config(); self.c.pop('submitter_ids')
    def tearDown(self): self.store.close(); self.temp.cleanup()
    def scan(self, text='https://test.atlassian.net/browse/ISOP-2067 @ssxx 合規後台提測', **extras):
        inbox = Inbox([[msg(1, text, **extras)]])
        return run_batch(self.store, inbox, self.c, self.state, jira_factory=lambda _: Resolver(), analyzer=fake_analysis), inbox

    def test_any_submitter_scan_previews_without_testing_sending_or_creating(self):
        result, inbox = self.scan()
        self.assertEqual(result['candidates'][0]['story'], 'ISOP-2037')
        self.assertEqual(result['candidates'][0]['issue'], 'ISOP-2067')
        self.assertEqual(result['candidates'][0]['tester_id'], 2)
        self.assertEqual(inbox.sent, [])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM jobs').fetchone()[0], 0)
        self.assertEqual(inbox.fetches[0]['timeout'], 0)

    def test_local_confirmation_runs_silently_then_bug_confirmation(self):
        result, inbox = self.scan()
        key = result['candidates'][0]['id']
        jobs = confirm(self.store, self.c, [key], result['revision'])
        pipeline = Mock(return_value=report())
        execute_batch(self.store, inbox, self.c, self.state, jobs, pipeline=pipeline, sleep=lambda _: None)
        pipeline.assert_called_once()
        self.assertEqual(inbox.sent, [])
        row = self.store.get(key)
        followup = Inbox([[msg(2, '/claim ' + key, user=2, chat=-20),
                           msg(3, f"/approve {key} {row['revision']} B1", user=2, chat=-20)]])
        jira = Resolver()
        submit_approved(self.store, followup, self.c, jira_factory=lambda _: jira, sleep=lambda _: None)
        self.assertEqual(len(jira.creates), 1)
        self.assertEqual(len(followup.sent), 1)
        self.assertTrue(all(body['chat_id'] == -20 for _, body in inbox.sent + followup.sent))

    def test_stale_confirmation_and_unresolved_parent_never_enqueue(self):
        result, _ = self.scan(); key = result['candidates'][0]['id']
        with self.assertRaises(ValueError): confirm(self.store, self.c, [key], 'old')
        result = run_batch(self.store, Inbox([[]]), self.c, self.state, jira_factory=lambda _: None)
        with self.assertRaises(ValueError): confirm(self.store, self.c, [key], result['revision'])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM jobs').fetchone()[0], 0)

    def test_story_owner_is_required_and_overrides_message_owner(self):
        result, _ = self.scan()
        key = result['candidates'][0]['id']
        self.c['stories']['ISOP-2037']['tester_id'] = None
        current = preview(self.store, self.c)
        with self.assertRaisesRegex(ValueError, '固定测试负责人'):
            confirm(self.store, self.c, [key], current['revision'])
        self.c['stories']['ISOP-2037']['tester_id'] = 2
        current = preview(self.store, self.c)
        confirm(self.store, self.c, [key], current['revision'])
        self.assertEqual(json.loads(self.store.get(key)['payload'])['tester_id'], 2)

    def test_links_in_selected_issue_hidden_links_and_replies(self):
        samples = [
            ('https://a.atlassian.net/issues?filter=-1&selectedIssue=ISOP-2040 @ssxx 大佬这个提测', {}),
            ('@ssxx 提測', {'entities': [{'type':'text_link','url':'https://a/browse/ISOP-2040'}]}),
            ('ISOP-2040 这个提测', {'reply_to_message': {'text':'ISOP-2040'}})]
        for text, extras in samples:
            self.store.db.execute('DELETE FROM intake_messages'); self.store.db.execute('DELETE FROM candidates'); self.store.db.execute('DELETE FROM meta'); self.store.db.commit()
            result, _ = self.scan(text, **extras)
            self.assertEqual(result['candidates'][0]['issue'], 'ISOP-2040')

    def test_pilot_restriction_and_duplicate_update(self):
        result, _ = self.scan(); self.c['pilot_story'] = 'ISOP-2027'
        current = preview(self.store, self.c)
        with self.assertRaises(ValueError): confirm(self.store, self.c, [current['candidates'][0]['id']], current['revision'])
        self.scan()
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM candidates').fetchone()[0], 1)

    def test_bounded_pagination_and_no_issue_no_candidate(self):
        inbox = Inbox([[msg(i, '普通聊天') for i in range(1, 101)]])
        result = scan_pending(self.store, inbox, self.c, max_pages=1)
        self.assertTrue(result['limit_reached']); self.assertEqual(self.store.offset(), 101)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM candidates').fetchone()[0], 0)

    def test_jira_resolution_requires_real_story_type_and_rejects_cycle(self):
        jira = object.__new__(Jira); jira.config = {'story_type_id': '10677'}
        jira.call = Mock(side_effect=[{'key':'ISOP-2067','fields':{'issuetype':{'id':'subtask'},'parent':{'key':'ISOP-2037'}}},
                                      {'key':'ISOP-2037','fields':{'issuetype':{'id':'10677'}}}])
        self.assertEqual(jira.resolve_story('ISOP-2067')['story'], 'ISOP-2037')
        jira.call = Mock(return_value={'key':'ISOP-2067','fields':{'issuetype':{'id':'subtask'},'parent':{'key':'ISOP-2067'}}})
        with self.assertRaises(ValueError): jira.resolve_story('ISOP-2067')


class AIIntakeTests(unittest.TestCase):
    setUp = BatchTests.setUp
    tearDown = BatchTests.tearDown
    scan = BatchTests.scan
    def test_failure_retains_messages_and_blocks_confirmation_then_retries(self):
        broken = Mock(side_effect=RuntimeError('offline'))
        result = run_batch(self.store, Inbox([[msg(1, 'ISOP-2037 已部署，可以验收了')]]), self.c, self.state,
                           jira_factory=lambda _: Resolver(), analyzer=broken)
        self.assertEqual(result['analysis']['status'], 'FAILED')
        self.assertEqual(result['pending_analysis'], 1)
        with self.assertRaises(ValueError): confirm(self.store, self.c, ['missing'], result['revision'])
        result = run_batch(self.store, Inbox([[]]), self.c, self.state,
                           jira_factory=lambda _: Resolver(), analyzer=fake_analysis)
        self.assertEqual(len(result['candidates']), 1)
        self.assertEqual(result['pending_analysis'], 0)

    def test_invented_issue_is_rejected_without_losing_evidence(self):
        def invent(*args):
            result = fake_analysis(*args)
            result['decisions'][0]['issue'] = 'ISOP-99999'
            return result
        result = run_batch(self.store, Inbox([[msg(1, 'ISOP-2037 可以验收了')]]), self.c, self.state,
                           jira_factory=lambda _: Resolver(), analyzer=invent)
        self.assertEqual(result['analysis']['status'], 'FAILED')
        self.assertEqual(result['candidates'], [])

    def test_withdrawal_is_visible_information_and_does_not_remove_notice(self):
        self.scan()
        def withdraw(*args):
            result = fake_analysis(*args)
            result['decisions'][0]['action'] = 'WITHDRAWN'
            return result
        result = run_batch(self.store, Inbox([[msg(2, 'ISOP-2067 先不要测')]]), self.c, self.state,
                           jira_factory=lambda _: Resolver(), analyzer=withdraw)
        self.assertEqual(len(result['candidates']), 1)
        self.assertEqual(len(result['candidates'][0]['source_messages']), 2)
        selected = next(p for p in result['candidates'] if p['ai_action'] == 'READY')
        self.assertEqual(confirm(self.store, self.c, [selected['id']], result['revision']), [selected['id']])


class ScanWindowTests(unittest.TestCase):
    setUp = BatchTests.setUp
    tearDown = BatchTests.tearDown

    def test_window_keeps_old_messages_for_later_selection_and_records_checkpoint(self):
        from qa_delivery.scan_history import parse_since
        since = parse_since('2026-09-10T15:00:00+08:00')
        result = run_batch(self.store, Inbox([[msg(1, 'ISOP-2037 可以测', date=since-1),
                                               msg(2, 'ISOP-2067 可以测', date=since+1)]]), self.c, self.state,
                           since=since, analyzer=fake_analysis, jira_factory=lambda _: Resolver())
        self.assertEqual([c['issue'] for c in result['candidates']], ['ISOP-2067'])
        self.assertEqual(self.store.db.execute('SELECT analyzed FROM intake_messages WHERE update_id=1').fetchone()[0], 2)
        result = run_batch(self.store, Inbox([[]]), self.c, self.state, since=since-10,
                           analyzer=fake_analysis, jira_factory=lambda _: Resolver())
        self.assertEqual(len(result['candidates']), 1)
        self.assertEqual(set(result['candidates'][0]['issues']), {'ISOP-2037','ISOP-2067'})
        self.assertEqual(result['scan']['previous_scan']['offset'], 3)
        daily = list((self.state/'scans').glob('*.json'))
        self.assertEqual(len(daily), 1)
        self.assertEqual(json.loads(daily[0].read_text())['scan_count'], 2)
        with self.assertRaises(ValueError): parse_since('2026-09-10T15:00:00')

    def test_non_isop_chat_skips_ai_and_failed_retry_reuses_folder(self):
        analyzer = Mock(side_effect=RuntimeError('offline'))
        result = run_batch(self.store, Inbox([[msg(1, '今天中午吃什么')]]), self.c, self.state,
                           analyzer=analyzer, jira_factory=lambda _: Resolver())
        analyzer.assert_not_called()
        self.assertEqual(result['analysis']['status'], 'NO_ISOP_MESSAGES')
        for inbox in (Inbox([[msg(2, 'ISOP-2037 已部署'), msg(3, '我在测试，不用理')]]), Inbox([[]])):
            run_batch(self.store, inbox, self.c, self.state, analyzer=analyzer, jira_factory=lambda _: Resolver())
        self.assertEqual(len(list((self.state/'intake').iterdir())), 1)
        data = analyzer.call_args.args[4]
        self.assertNotIn(3, data['new_message_ids'])


class LocalMappingTests(unittest.TestCase):
    def test_only_explicit_subtask_lines_are_mapped_and_conflicts_rejected(self):
        from qa_delivery.intake import local_story_index
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for story, content in [('ISOP-2027', '- 子任务：[ISOP-2051](https://test/ISOP-2051)\n参考 ISOP-9999'),
                                   ('ISOP-2022', '- 子任务：ISOP-2044')]:
                (root/story).mkdir(); (root/story/'design.md').write_text(content)
            self.assertEqual(local_story_index(root)['ISOP-2051'], 'ISOP-2027')
            self.assertNotIn('ISOP-9999', local_story_index(root))
            (root/'ISOP-2022'/'design.md').write_text('- 子任务：ISOP-2051')
            self.assertNotIn('ISOP-2051', local_story_index(root))
