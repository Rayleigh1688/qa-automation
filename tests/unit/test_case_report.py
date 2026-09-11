import csv
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from qa_core.case_report import FIELDS, csv_text, execution_status, join_results, load_cases, write_views


def case(key):
    return dict(zip(FIELDS, [key, 'API', '/example', '缺必填参数', '独立样本', '省略id', '拒绝且无副作用', '冒烟', 'C01']))


class CaseReportTests(unittest.TestCase):
    def test_transport_error_is_not_an_observed_http_failure(self):
        self.assertEqual(execution_status({'status': 'FAIL', 'observation': {'http': None}}), 'ERROR')
        self.assertEqual(execution_status({'status': 'FAIL', 'observation': {'http': 500}}), 'FAIL')
        self.assertEqual(execution_status({'status': 'BLOCKED'}), 'NOT_RUN')

    def test_missing_execution_is_not_pass_and_setup_not_in_denominator(self):
        rows = join_results([case('A'), case('B')], {'results': [
            {'id': 'A', 'status': 'PASS', 'actual': '拒绝且资料不变', 'evidence': 'evidence.json'}]})
        self.assertEqual([r['执行结果'] for r in rows], ['PASS', 'NOT_RUN'])
        with self.assertRaises(ValueError):
            join_results([case('A')], {'results': [{'id': 'login', 'status': 'PASS', 'actual': 'ok', 'evidence': 'x'}]})

    def test_no_silent_retry_merge_or_unknown_status(self):
        record = {'id': 'A', 'status': 'FAIL', 'actual': '接受了非法值', 'evidence': 'x'}
        for records in [[record, {**record, 'status': 'PASS'}], [{**record, 'status': 'PARTIAL'}],
                        [{**record, 'evidence': ''}], [{**record, 'actual': ''}]]:
            with self.assertRaises(ValueError):
                join_results([case('A')], {'results': records})

    def test_export_counts_and_no_overwrite(self):
        cases = [case(k) for k in ['A', 'B', 'C', 'D']]
        results = [{'id': k, 'status': s, 'actual': '说明', 'evidence': 'x'}
                   for k, s in zip(['A', 'B', 'C'], ['PASS', 'FAIL', 'ERROR'])]
        with tempfile.TemporaryDirectory() as folder:
            summary = write_views(folder, cases, {'results': results, 'mode': 'historical-summary'})
            self.assertEqual(summary['total'], 4)
            self.assertEqual(summary['executed'], 2)
            self.assertEqual([summary[s] for s in ['PASS', 'FAIL', 'ERROR', 'NOT_RUN']], [1, 1, 1, 1])
            self.assertEqual(load_cases(Path(folder) / 'cases.csv'), cases)
            with (Path(folder) / 'failures.csv').open(encoding='utf-8-sig') as f:
                self.assertEqual([r['用例编号'] for r in csv.DictReader(f)], ['B'])
            with self.assertRaises(ValueError):
                write_views(folder, cases, {'results': results})

    def test_untrusted_text_cannot_inject_html_or_csv_formula(self):
        record = {'id': 'A', 'status': 'FAIL', 'actual': '<script>alert(1)</script>', 'evidence': 'javascript:alert(1)'}
        with tempfile.TemporaryDirectory() as folder:
            write_views(folder, [case('A')], {'results': [record]})
            html = (Path(folder) / 'results.html').read_text()
            self.assertNotIn('<script>alert(1)</script>', html)
            self.assertNotIn('href="javascript:', html)
            self.assertIn('&lt;script&gt;', html)
        text = csv_text([{'value': '=HYPERLINK("x")'}], ['value'])
        self.assertEqual(next(csv.DictReader(io.StringIO(text.lstrip('\ufeff'))))['value'], '\'=HYPERLINK("x")')

    def test_minimal_views_keep_results_and_filters_without_dead_downloads(self):
        from html.parser import HTMLParser
        class Links(HTMLParser):
            def __init__(self):
                super().__init__(); self.targets = []
            def handle_starttag(self, tag, attrs):
                if tag == 'a': self.targets.append(dict(attrs)['href'])
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            summary = write_views(target, [case('A')], {'results': []}, extra_views=False)
            self.assertEqual(summary['NOT_RUN'], 1)
            self.assertEqual({p.name for p in target.iterdir()}, {'results.csv', 'results.html'})
            html = (target / 'results.html').read_text()
            links = Links(); links.feed(html)
            self.assertEqual(links.targets, ['results.csv'])
            self.assertIn('id="status"', html)
            self.assertIn('id="search"', html)
            with (target / 'results.csv').open(encoding='utf-8-sig') as stream:
                self.assertEqual(next(csv.DictReader(stream))['执行结果'], 'NOT_RUN')

    def test_catalogue_requires_clear_steps_and_unique_ids(self):
        for rows in [[case('A'), case('A')], [{**case('A'), '预期结果': ''}]]:
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'cases.csv'
                path.write_text(csv_text(rows, FIELDS))
                with self.assertRaises(ValueError):
                    load_cases(path)

    def test_existing_api_runner_adds_views_without_relabeling_script_errors_as_bugs(self):
        from filbet.requirement_api import write_reports
        cases = [{'id': key, 'case_ids': ['ISOP-2027-C12'], 'kind': 'positive',
                  'title': key, 'request': {'method': 'GET', 'path': '/admin/kyc/review/list'},
                  'expect': 'success', 'checks': []} for key in ['A', 'B', 'C']]
        results = [{'id': key, 'case_ids': ['ISOP-2027-C12'], 'kind': 'positive',
                    'status': status, 'details': [detail]} for key, status, detail in [
                    ('A', 'FAIL', 'request/evaluation exception; raw details suppressed'),
                    ('B', 'FAIL', 'expected HTTP 200 and business status true'),
                    ('C', 'BLOCKED', 'missing fixture')]]
        report = {'requirement': 'ISOP-2027', 'run_at': '2026-09-11', 'environment': 'FAT',
                  'deployment': '未提供', 'cases_sha256': 'test', 'results': results}
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'run'
            write_reports(target, report, {'cases': cases})
            self.assertTrue((target / 'report.md').exists())
            self.assertEqual(json.loads((target / 'result.json').read_text()), report)
            summary = json.loads((target / 'views/summary.json').read_text())
            self.assertEqual([summary[s] for s in ['FAIL', 'ERROR', 'NOT_RUN']], [1, 1, 1])


if __name__ == '__main__':
    unittest.main()
