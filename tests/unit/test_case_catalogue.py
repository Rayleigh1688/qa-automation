"""Business coverage stays concise; data expansion and execution IDs stay complete."""
import copy
import csv
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

from support import ROOT
from requirement_paths import requirement_dir, requirement_dirs
from filbet.requirement_adapter import METHODS
from qa_core.case_catalogue import API_FIELDS, design_rows, overview_rows, export_catalogues
from qa_core.case_design import DESIGN_FIELDS, has_design_definition
from qa_core.case_report import FIELDS
from qa_core.execution_plan import load


class CaseCatalogueTests(unittest.TestCase):
    def setUp(self):
        self.folder = requirement_dir(ROOT, 'ISOP-2027')
        self.plan, self.cases, _ = load(self.folder / 'plan.json', METHODS)
        self.temp = tempfile.TemporaryDirectory()
        self.out = Path(self.temp.name) / 'ISOP-2027'
        self.out.mkdir()
        (self.out / 'test-cases.md').write_bytes((self.folder / 'test-cases.md').read_bytes())

    def tearDown(self):
        self.temp.cleanup()

    def test_overview_is_business_scope_and_api_rows_keep_every_automatic_combination(self):
        original = copy.deepcopy(self.cases)
        overview_count, api_count = export_catalogues(self.out, plan=self.plan, cases=self.cases)
        with (self.out / 'cases.csv').open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            self.assertEqual(reader.fieldnames, FIELDS)
            overview = list(reader)
        with (self.out / 'api/data-cases.csv').open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            self.assertEqual(reader.fieldnames, API_FIELDS)
            data = list(reader)
        # Remote manual C18 expands business acceptance without inventing executable API coverage.
        self.assertEqual(overview_count, len(self.plan['acceptance_ids']) + 1)
        known = {r['用例编号'] for r in overview}
        self.assertEqual(known, {'ISOP-2027-' + ref for ref in self.plan['acceptance_ids']} | {'ISOP-2027-C18'})
        self.assertTrue(all('ISOP-2027-C18' not in r['总用例编号'].split(',') for r in data))
        self.assertNotIn('${', json.dumps(overview, ensure_ascii=False))
        self.assertNotIn('body.status', json.dumps(overview, ensure_ascii=False))
        expected = {c['id'] for c in self.cases if c['delivery']['mode'] == 'automatic'}
        self.assertEqual({r['执行用例编号'] for r in data}, expected)
        self.assertEqual(api_count, len(expected))
        self.assertTrue(all(set(r['总用例编号'].split(',')) <= known for r in data))
        state = next(r for r in data if r['执行用例编号'].endswith(':kyc-state-3'))
        self.assertIs(type(json.loads(state['输入变量'])['data']['status']), int)
        self.assertEqual(json.loads(state['输入变量'])['data']['status'], 3)
        self.assertIn('body.status', state['预期/断言'])
        self.assertEqual(self.cases, original)

    def test_bad_link_does_not_overwrite_generated_overview(self):
        marker = self.out / 'cases.csv'
        marker.write_text('existing view')
        self.cases[0]['review']['验收点'] = 'C999'
        with self.assertRaises(ValueError):
            export_catalogues(self.out, plan=self.plan, cases=self.cases)
        self.assertEqual(marker.read_text(), 'existing view')
        self.assertFalse((self.out / 'api/data-cases.csv').exists())

    def test_design_parser_stops_before_execution_history_and_rejects_duplicate_ids(self):
        path = self.out / 'test-cases.md'
        rows = design_rows(path, self.out.name)
        self.assertEqual(len(rows), 18)
        self.assertEqual(len(overview_rows(rows, self.out.name)), 18)
        text = path.read_text()
        row = next(line for line in text.splitlines() if line.startswith('| ISOP-2027-C01 |'))
        path.write_text(text.replace(row, row + '\n' + row))
        with self.assertRaises(ValueError):
            design_rows(path, self.out.name)

    def test_other_stories_use_their_own_design_and_preserve_legacy_data(self):
        from qa_core.case_catalogue import legacy_api_rows
        folders = requirement_dirs(ROOT, include_history=True)
        snapshots = ROOT / 'requirements/history/archived-20261005/snapshots'
        snapshot_folders = sorted(snapshots.glob('ISOP-*'))
        self.assertTrue({'ISOP-2090', 'ISOP-2103', 'ISOP-2116', 'ISOP-2120'} <=
                        {folder.name for folder in snapshot_folders})
        folders += snapshot_folders
        for folder in folders:
            path = folder / 'test-cases.md'
            if not has_design_definition(path):
                self.assertFalse((folder / 'cases.csv').exists(),
                                 'review priorities must not carry a generated case catalogue')
                self.assertFalse((folder / 'plan.json').exists())
                self.assertFalse((folder / 'api/cases.json').exists())
                continue
            with self.subTest(story=folder.name):
                overview = overview_rows(design_rows(path, folder.name), folder.name)
                known = {r['用例编号'] for r in overview}
                self.assertTrue(all(k.startswith(folder.name + '-') or k.startswith('R') for k in known))
                source = folder / 'api/cases.json'
                if source.is_file():
                    suite = json.loads(source.read_text())
                    original = copy.deepcopy(suite)
                    data = legacy_api_rows(suite, known)
                    self.assertEqual(len(data), len(suite['cases']))
                    for case, row in zip(suite['cases'], data):
                        if case.get('request'):
                            self.assertEqual(json.loads(row['请求/步骤']), case['request'])
                    self.assertEqual(suite, original)


class CaseCatalogueCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        spec = importlib.util.spec_from_file_location(
            'case_catalogue_cli', ROOT / 'scripts/export-requirement-cases.py')
        self.cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.cli)
        self.cli.ROOT = self.root

    def folder(self, story, text):
        folder = self.root / 'requirements' / story
        folder.mkdir(parents=True)
        (folder / 'test-cases.md').write_text(text, encoding='utf-8')
        return folder

    def formal_design(self, story):
        row = [story + '-C01', '高 / AC-01', '独立查询', '本批隔离样本',
               '查询一次', '返回已确认的数据且无写入', 'API', '—', 'NOT_RUN', 'QA']
        return '\n'.join(['# 正式用例',
                          '| ' + ' | '.join(DESIGN_FIELDS) + ' |',
                          '| ' + ' | '.join(['---'] * len(DESIGN_FIELDS)) + ' |',
                          '| ' + ' | '.join(row) + ' |'])

    def test_detection_requires_a_formal_declaration_not_prose_or_id_only_table(self):
        folder = self.folder('ISOP-1', '# 初步测试设计\n## 测试重点\n- 核对已确认规则\n')
        path = folder / 'test-cases.md'
        self.assertFalse(has_design_definition(path))
        path.write_text('| Case ID | 备注 |\n| ISOP-1-C01 | 旧索引 |', encoding='utf-8')
        self.assertFalse(has_design_definition(path))
        path.write_text(self.formal_design('ISOP-1'), encoding='utf-8')
        self.assertTrue(has_design_definition(path))
        # A malformed API sibling is still a declared design, not a review.
        path.write_text('# 测试重点', encoding='utf-8')
        (folder / 'api').mkdir()
        (folder / 'api/test-cases.md').write_text('<!-- case-cards:v2 -->', encoding='utf-8')
        self.assertTrue(has_design_definition(path))

    def test_all_exports_ready_cases_and_explicitly_skips_review_without_writes(self):
        review = self.folder('ISOP-1', '# 初步测试设计\n- 尚待确认预期\n')
        # Skip before loading execution assets, and preserve existing files.
        (review / 'plan.json').write_text('not a plan', encoding='utf-8')
        marker = review / 'cases.csv'
        marker.write_text('existing file', encoding='utf-8')
        ready = self.folder('ISOP-2', self.formal_design('ISOP-2'))
        before = {p.relative_to(review): p.read_bytes() for p in review.rglob('*') if p.is_file()}
        output = io.StringIO()
        with redirect_stdout(output):
            self.cli.main(['--all'])
        self.assertIn('ISOP-1: 评审未就绪', output.getvalue())
        self.assertIn('skipped; no login', output.getvalue())
        self.assertIn('ISOP-2: overview=1', output.getvalue())
        self.assertEqual(before, {p.relative_to(review): p.read_bytes()
                                 for p in review.rglob('*') if p.is_file()})
        with (ready / 'cases.csv').open(encoding='utf-8-sig', newline='') as stream:
            self.assertEqual([r['用例编号'] for r in csv.DictReader(stream)], ['ISOP-2-C01'])
        self.assertFalse((ready / 'api').exists())

    def test_explicit_review_rejects_entire_selection_before_writing_any_file(self):
        ready = self.folder('ISOP-1', self.formal_design('ISOP-1'))
        review = self.folder('ISOP-2', '# 初步测试设计\n- 尚待确认预期\n')
        (review / 'plan.json').write_text('not a plan', encoding='utf-8')
        before = {p.relative_to(self.root): p.read_bytes()
                  for p in self.root.rglob('*') if p.is_file()}
        errors = io.StringIO()
        with redirect_stderr(errors), self.assertRaises(SystemExit) as failure:
            self.cli.main(['ISOP-1', 'ISOP-2'])
        self.assertEqual(failure.exception.code, 2)
        self.assertIn('ISOP-2: 评审未就绪', errors.getvalue())
        self.assertIn('未写入文件', errors.getvalue())
        self.assertEqual(before, {p.relative_to(self.root): p.read_bytes()
                                 for p in self.root.rglob('*') if p.is_file()})
        self.assertFalse((ready / 'cases.csv').exists())

    def test_declared_but_damaged_design_is_an_error_not_a_review_skip(self):
        ready = self.folder('ISOP-1', self.formal_design('ISOP-1'))
        damaged = self.folder('ISOP-2', '')
        path = damaged / 'test-cases.md'
        formal = self.formal_design('ISOP-2')
        variants = [
            '<!-- case-cards:v1 -->\n# missing closing marker',
            formal.replace('| 负责人 |', '| unknown owner field |'),
            formal.replace(' | QA |', ' | QA | extra |'),
        ]
        for text in variants:
            with self.subTest(format=text.splitlines()[0]):
                path.write_text(text, encoding='utf-8')
                self.assertTrue(has_design_definition(path))
                output = io.StringIO()
                with redirect_stdout(output), self.assertRaises(ValueError):
                    self.cli.main(['--all'])
                self.assertNotIn('ISOP-2: 评审未就绪', output.getvalue())
                self.assertFalse((ready / 'cases.csv').exists())
                self.assertFalse((damaged / 'cases.csv').exists())


if __name__ == '__main__':
    unittest.main()
