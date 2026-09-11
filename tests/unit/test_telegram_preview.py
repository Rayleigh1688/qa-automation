"""Requirement-level selection and local rendering cannot widen test authorization."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from support import ROOT
from qa_delivery.batch import refresh_preview
from qa_delivery.intake import confirm, preview, select_candidates
from qa_delivery.preview_report import render_preview
from qa_delivery.pipeline import run_pipeline
from qa_delivery.state import Store, validate_config


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for story in ('ISOP-2022', 'ISOP-2027', 'ISOP-2028'):
            folder = self.root / 'requirements' / story; folder.mkdir(parents=True)
            (folder / 'design.md').write_text(f'# {story}：测试需求 — 测试设计\n')
            (folder / 'test-cases.md').write_text('验收用例')
        self.state = self.root / 'reports'
        self.store = Store(self.state / 'queue.sqlite3'); self.addCleanup(self.store.close)
        patcher = patch('qa_delivery.pipeline.ROOT', self.root)
        patcher.start(); self.addCleanup(patcher.stop)
        self.config = {'stories': {s: {'tester_id': 2, 'environments': ['FAT', 'UAT']}
                                  for s in ('ISOP-2022', 'ISOP-2027', 'ISOP-9999')}}

    def candidate(self, key, story='ISOP-2022', issue='ISOP-2085', **changes):
        data = {'story': story, 'issue': issue, 'text': issue + ' original message', 'message_id': key,
                'environment': 'FAT', 'environment_source': 'local default; confirm environment',
                'build': '未提供', 'scopes': ['api', 'ui'], 'ai_action': 'READY', 'reason': 'message evidence',
                'scope_note': 'scope evidence', 'resolution': 'test fixture', **changes}
        with self.store.db:
            self.store.db.execute('INSERT INTO candidates VALUES(?,?,?)', (key, json.dumps(data), 'PENDING'))

    def test_only_local_requirements_are_selectable_and_unmatched_evidence_is_retained(self):
        self.candidate('a')
        self.candidate('b', story='ISOP-9999', issue='ISOP-9999')
        self.candidate('c', story=None, issue='ISOP-8888')
        current = preview(self.store, self.config)
        self.assertEqual([p['story'] for p in current['candidates']], ['ISOP-2022'])
        self.assertEqual(len(current['unmatched']), 2)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM candidates').fetchone()[0], 3)
        for key in ('b', 'c'):
            with self.assertRaises(ValueError):
                confirm(self.store, self.config, [key], current['revision'])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM jobs').fetchone()[0], 0)
        with self.assertRaisesRegex(ValueError, '不在当前'):
            select_candidates(current, requirements='ISOP-2028')

    def test_requirement_selection_confirms_all_merged_subtasks_but_nothing_else(self):
        self.candidate('a')
        self.candidate('b', issue='ISOP-2044')
        self.candidate('c', story='ISOP-2027', issue='ISOP-2051')
        current = preview(self.store, self.config)
        selected = select_candidates(current, requirements='ISOP-2022')
        self.assertEqual(selected, ['a'])
        self.assertEqual(select_candidates(current, candidates='a'), selected)
        confirm(self.store, self.config, selected, current['revision'])
        states = dict(self.store.db.execute('SELECT id,status FROM candidates'))
        self.assertEqual(states, {'a': 'CONFIRMED', 'b': 'CONFIRMED', 'c': 'PENDING'})
        payload = json.loads(self.store.get('a')['payload'])
        self.assertEqual(set(payload['issues']), {'ISOP-2085', 'ISOP-2044'})

    def test_ambiguous_batches_require_explicit_ids_and_render_once_per_requirement(self):
        self.candidate('a')
        self.candidate('b', environment='UAT')
        self.candidate('c', build='build-2')
        self.candidate('d', scopes=['api'])
        current = preview(self.store, self.config)
        with self.assertRaisesRegex(ValueError, '多个环境、版本或范围'):
            select_candidates(current, requirements='ISOP-2022')
        self.assertEqual(select_candidates(current, candidates='b'), ['b'])
        output = render_preview(current, self.state)
        self.assertEqual(output.count('| ISOP-2022 |'), 1)
        self.assertIn('4 批次需分别选范围', output)
        self.assertNotIn('original message', output)
        self.assertEqual(len(current['candidates']), 4)

    def test_selection_rejects_empty_duplicate_mixed_unknown_and_stale_input(self):
        self.candidate('a')
        current = preview(self.store, self.config)
        for args in ({}, {'requirements': 'ISOP-2022', 'candidates': 'a'}, {'requirements': 'ISOP-2022,'},
                     {'requirements': 'ISOP-2022,ISOP-2022'}, {'candidates': 'missing'}):
            with self.assertRaises(ValueError): select_candidates(current, **args)
        self.candidate('b', issue='ISOP-2044')
        with self.assertRaisesRegex(ValueError, '清单已改变'):
            confirm(self.store, self.config, ['a'], current['revision'])

    def test_compact_output_keeps_uncertainty_without_dumping_blocked_cases(self):
        self.candidate('a', story='ISOP-2027', issue='ISOP-2027', environment='UAT', ai_action='UNCERTAIN')
        current = preview(self.store, self.config)
        current['candidates'][0]['execution'] = {'blocked': {f'API-{n}': 'write not allowed' for n in range(65)}}
        output = render_preview(current, self.state)
        self.assertIn('待核实（非明确提测）', output)
        self.assertNotIn('API-0', output)
        self.assertNotIn('original message', output)
        self.assertIn('手工UI', output)
        self.assertLess(len(output.splitlines()), 18)
        current.update(pending_analysis=4, analysis={'status': 'FAILED', 'detail': 'Codex CLI not found'})
        output = render_preview(current, self.state)
        self.assertIn('扫描未完成', output)
        self.assertNotIn('run --requirements', output)

    def test_mixed_message_actions_preserved_and_local_refresh_does_not_mutate_queue(self):
        self.candidate('a')
        self.candidate('b', issue='ISOP-2044', ai_action='WITHDRAWN')
        saved = {**preview(self.store, self.config), 'updates': 2, 'pending_analysis': 0,
                 'analysis': {'status': 'ANALYZED'}, 'scan': {'finished_at': '2026-09-11T08:14:37Z'}}
        (self.state / 'preview.json').write_text(json.dumps(saved))
        before = hashlib.sha256((self.state / 'queue.sqlite3').read_bytes()).hexdigest()
        refreshed = refresh_preview(self.config, self.state)
        self.assertEqual(hashlib.sha256((self.state / 'queue.sqlite3').read_bytes()).hexdigest(), before)
        self.assertEqual(refreshed['scan'], saved['scan'])
        self.assertEqual(refreshed['revision'], saved['revision'])
        self.assertIn('另有备注', (self.state / 'preview.md').read_text())
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM jobs').fetchone()[0], 0)

    def test_ui_requirement_limit_removes_legacy_api_scope_from_confirmation_and_execution(self):
        self.candidate('a')
        old = preview(self.store, self.config)
        self.config['stories']['ISOP-2022']['test_scopes'] = ['ui']
        self.config['environments'] = {'FAT': {'env_file': '.env.fat', 'version_probes': []}}
        current = preview(self.store, self.config)
        row = current['candidates'][0]
        self.assertEqual(row['scopes'], ['ui'])
        self.assertEqual(row['intake_scopes'], ['api', 'ui'])
        self.assertNotEqual(current['revision'], old['revision'])
        self.assertIn('| 手工UI |', render_preview(current, self.state))
        confirm(self.store, self.config, ['a'], current['revision'])
        with patch('qa_delivery.pipeline.command') as command, patch('qa_delivery.pipeline.acceptance', return_value=({}, {'C01'})):
            report = run_pipeline(self.config, self.store.get('a'), self.state / 'run-ui')
        command.assert_not_called()
        self.assertEqual([r['id'] for r in report['results']], ['UI'])
        self.assertEqual(report['results'][0]['status'], 'NOT_RUN')
        original = json.loads(self.store.db.execute('SELECT payload FROM candidates WHERE id=?', ('a',)).fetchone()[0])
        self.assertEqual(original['scopes'], ['api', 'ui'])

    def test_requirement_limit_never_expands_message_scope_or_accepts_empty_intersection(self):
        self.candidate('a', scopes=['api'])
        self.config['stories']['ISOP-2022']['test_scopes'] = ['ui']
        current = preview(self.store, self.config)
        self.assertEqual(current['candidates'][0]['scopes'], [])
        with self.assertRaisesRegex(ValueError, '范围不相符'):
            confirm(self.store, self.config, ['a'], current['revision'])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM jobs').fetchone()[0], 0)

    def test_requirement_scope_configuration_is_validated(self):
        from test_telegram_delivery import config
        c = config()
        for invalid in ([], ['api', 'api'], ['browser'], 'ui', None, [{}]):
            c['stories']['ISOP-2037']['test_scopes'] = invalid
            with self.assertRaisesRegex(ValueError, 'test_scopes'):
                validate_config(c)
        c['stories']['ISOP-2037']['test_scopes'] = ['ui']
        self.assertIs(validate_config(c), c)


if __name__ == '__main__':
    unittest.main()
