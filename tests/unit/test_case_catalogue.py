"""Business coverage stays concise; data expansion and execution IDs stay complete."""
import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest

from support import ROOT
from filbet.requirement_adapter import METHODS
from qa_core.case_catalogue import API_FIELDS, design_rows, overview_rows, export_catalogues
from qa_core.execution_plan import load


class CaseCatalogueTests(unittest.TestCase):
    def setUp(self):
        self.folder = ROOT / 'requirements/ISOP-2027'
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
            overview = list(csv.DictReader(stream))
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
        for folder in (ROOT / 'requirements').glob('ISOP-*'):
            with self.subTest(story=folder.name):
                overview = overview_rows(design_rows(folder / 'test-cases.md', folder.name), folder.name)
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


if __name__ == '__main__':
    unittest.main()
