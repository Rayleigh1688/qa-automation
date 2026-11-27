import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from qa_core.case_report import CATALOGUE_FIELDS, FIELDS, csv_text, execution_status, join_results, load_cases, write_views


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

    def test_api_outcome_view_shows_only_actual_pass_and_fail(self):
        cases = [case(key) for key in ('A', 'B', 'C', 'D', 'E')]
        report = {'results': [
            {'id': 'A', 'status': 'PASS', 'actual': '请求符合预期', 'evidence': 'x'},
            {'id': 'B', 'status': 'FAIL', 'actual': '响应不符合预期', 'evidence': 'x'},
            {'id': 'C', 'status': 'ERROR', 'actual': '登录失败', 'evidence': 'x'},
            {'id': 'D', 'status': 'NOT_RUN', 'actual': '样本未准备'},
        ]}
        original = json.dumps(report)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            summary = write_views(target, cases, report, api_outcomes_only=True)
            self.assertEqual([summary[s] for s in ('PASS', 'FAIL', 'total', 'executed')], [1, 1, 2, 2])
            self.assertTrue({'NOT_RUN', 'ERROR'}.isdisjoint(summary))
            self.assertFalse((target / 'pending.csv').exists())
            html = (target / 'results.html').read_text()
            for omitted in ('NOT_RUN', 'ERROR', '前置条件', '登录失败', '样本未准备', 'pending.csv'):
                self.assertNotIn(omitted, html)
            with (target / 'results.csv').open(encoding='utf-8-sig') as stream:
                reader = csv.DictReader(stream)
                self.assertNotIn('前置条件', reader.fieldnames)
                self.assertEqual([(r['用例编号'], r['执行结果']) for r in reader], [('A', 'PASS'), ('B', 'FAIL')])
        self.assertEqual(json.dumps(report), original)

    def test_api_outcome_view_with_no_outcomes_has_empty_report(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            summary = write_views(target, [case('A')], {'results': []}, extra_views=False, api_outcomes_only=True)
            self.assertEqual([summary[s] for s in ('PASS', 'FAIL', 'total')], [0, 0, 0])
            html = (target / 'results.html').read_text()
            self.assertIn('本批没有可展示的接口判定', html)
            self.assertNotIn('data-status=', html)
            with (target / 'results.csv').open(encoding='utf-8-sig') as stream:
                self.assertEqual(list(csv.DictReader(stream)), [])

    def test_api_report_renders_step_exchange_and_assertion_values(self):
        step = {
            'id': 'vip_config', 'status': 'FAIL', 'elapsed_ms': 128,
            'request': {'method': 'GET', 'path': '/promo/vip/config', 'query': {'page': 1}},
            'observation': {'http': 200, 'business_status': True},
            'response': {
                'body': {'message': 'Success', 'data': {'updated_name': '<script>alert(1)</script>'}},
                'decode_status': 'decoded', 'truncated': True, 'redacted': True, 'omitted_fields': 12,
            },
            'assertions': [
                {'path': 'http', 'op': 'eq', 'expected': 200, 'actual': 200, 'status': 'PASS'},
                {'path': 'body', 'op': 'fields_absent_or', 'status': 'FAIL',
                 'expected': {'updated_uid': [None, '', 0], 'updated_name': []}, 'actual': '<redacted>',
                 'field_observations': {'updated_uid': {'integer_zero': 31}, 'updated_name': {'nonempty_string': 1}},
                 'unexpected_fields': ['updated_name']},
            ],
        }
        report = {'requirement': 'ISOP-2375', 'environment': 'FAT', 'run_id': 'fixture',
                  'source_time': '2026-11-27T09:00:00+00:00',
                  'results': [{'id': 'A', 'status': 'FAIL', 'actual': '员工名称未清空',
                               'evidence': 'result.json', 'steps': [step]}]}
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            (target / 'result.json').write_text(json.dumps(report), encoding='utf-8')
            write_views(target, [case('A')], report, extra_views=False, api_outcomes_only=True)
            html = (target / 'results.html').read_text(encoding='utf-8')
        for token in ('ISOP-2375 API 测试报告', '2026-11-27 17:00:00', '断言对照',
                      'GET /promo/vip/config', 'HTTP 200', '128 ms', 'Success', '预览已截断',
                      '样本中省略 12 个其他字段', '整数 0 × 31', '预期字段缺失 · 实际 非空字符串 × 1',
                      '不符合的字段 updated_name', 'href="result.json"'):
            self.assertIn(token, html)
        self.assertLess(html.index('失败字段（完整响应统计）'), html.index('响应预览（已脱敏）'))
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)
        self.assertNotIn('<script>alert(1)</script>', html)

    def test_unified_rebuild_projects_api_only_runs_and_preserves_other_views(self):
        runner = Path(__file__).resolve().parents[2] / 'scripts' / 'run-requirement.py'
        for other_type, profile, statuses in (
            ('API', None, ['PASS']), ('FLOW', None, ['PASS', 'NOT_RUN']),
            ('API', 'regression', ['PASS', 'NOT_RUN']),
        ):
            with self.subTest(other_type=other_type, profile=profile), tempfile.TemporaryDirectory() as folder:
                source = Path(folder) / 'source'
                source.mkdir()
                cases = [case('A'), {**case('B'), '类型': other_type}]
                raw = {'requirement': 'ISOP-9999', 'mode': 'execution', 'profile': profile, 'results': [
                    {'id': 'A', 'status': 'PASS', 'actual': '通过', 'evidence': 'fake'},
                    {'id': 'B', 'status': 'NOT_RUN', 'actual': '样本未准备'},
                ]}
                raw_text = json.dumps(raw)
                (source / 'result.json').write_text(raw_text)
                (source / 'cases.snapshot.json').write_text(json.dumps(cases))
                finished = subprocess.run([sys.executable, str(runner), 'ISOP-9999', '--rebuild', str(source)],
                                          check=True, capture_output=True, text=True, timeout=10)
                target, = source.parent.glob('source-views-*')
                self.assertIn(str(target / 'results.html'), finished.stdout)
                with (target / 'results.csv').open(encoding='utf-8-sig') as stream:
                    self.assertEqual([row['执行结果'] for row in csv.DictReader(stream)], statuses)
                self.assertEqual((source / 'result.json').read_text(), raw_text)

    def test_readonly_reassessment_shows_original_provenance_and_partial_scope(self):
        report = {'results': [{'id': 'A', 'status': 'PASS', 'actual': '已核只读子项', 'evidence': 'x'}],
                  'run_id': 'review-2', 'source_run_id': 'original-1',
                  'source_time': '2026-10-12T16:34:41+08:00',
                  'mode': 'recorded-readonly-reassessment',
                  'classification': {'reviewed_at': '2026-10-12T16:39:23+08:00'},
                  'scope': 'GET /example; <script>scope()</script>',
                  'boundaries': ['未验证真实入账', '<img src=x onerror=alert(1)>']}
        with tempfile.TemporaryDirectory() as folder:
            summary = write_views(folder, [case('A')], report, extra_views=False)
            html = (Path(folder) / 'results.html').read_text()
            self.assertIn('本次未重新测试；新请求0次', html)
            self.assertIn('原采集批次：original-1', html)
            self.assertIn('原采集时间：2026-10-12 16:34:41（UTC+8）', html)
            self.assertIn('重分类复核时间：2026-10-12 16:39:23（UTC+8）', html)
            self.assertIn('不能自动代表复合功能用例整体通过', html)
            self.assertIn('未验证真实入账', html)
            self.assertIn('&lt;script&gt;scope()&lt;/script&gt;', html)
            self.assertNotIn('<script>scope()</script>', html)
            self.assertNotIn('<img src=x onerror=alert(1)>', html)
            self.assertEqual(summary['source_time'], report['source_time'])
            self.assertEqual(summary['PASS'], 1)
            with (Path(folder) / 'results.csv').open(encoding='utf-8-sig') as stream:
                self.assertEqual(next(csv.DictReader(stream))['执行结果'], 'PASS')

    def test_directed_readonly_view_labels_live_subitems_without_reassessment_claim(self):
        with tempfile.TemporaryDirectory() as folder:
            write_views(folder, [case('A')], {'results': [], 'mode': 'directed-readonly',
                        'scope': 'report arithmetic', 'boundaries': ['未取得实际CSV']}, extra_views=False)
            html = (Path(folder) / 'results.html').read_text()
            self.assertIn('定向只读实测', html)
            self.assertIn('本报告范围：report arithmetic', html)
            self.assertIn('未取得实际CSV', html)
            self.assertNotIn('新请求0次', html)

    def test_long_multiple_evidence_references_render_as_text(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            original = target / 'private-evidence.json'
            original.write_text('{}')
            refs = '; '.join([str(original)] * 100)
            self.assertGreater(len(refs), 4096)
            write_views(target / 'views', [case('A')], {'results': [
                {'id': 'A', 'status': 'FAIL', 'actual': '保留原始失败', 'evidence': refs}]}, extra_views=False)
            html = (target / 'views/results.html').read_text()
            self.assertIn(refs, html)
            self.assertNotIn('查看证据</a>', html)
            self.assertTrue(original.is_file())
            with (target / 'views/results.csv').open(encoding='utf-8-sig') as stream:
                self.assertEqual(next(csv.DictReader(stream))['证据'], refs)

    def test_catalogue_requires_clear_steps_and_unique_ids(self):
        for rows in [[case('A'), case('A')], [{**case('A'), '预期结果': ''}]]:
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'cases.csv'
                path.write_text(csv_text(rows, FIELDS))
                with self.assertRaises(ValueError):
                    load_cases(path)

    def test_design_catalogue_rejects_invalid_metadata_and_projects_only_execution_fields(self):
        record = {**case('A'), '类型': '功能', '状态': 'PASS', '负责人': 'Davinci', '验证方式': 'UI+API'}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'cases.csv'
            path.write_text(csv_text([record], CATALOGUE_FIELDS))
            rows = load_cases(path)
            self.assertEqual(rows, [{**case('A'), '类型': 'FLOW'}])
            self.assertEqual(join_results(rows, {'results': []})[0]['执行结果'], 'NOT_RUN')
            for changed in ({'类型': 'UI'}, {'类型': 'API'}, {'状态': '已完成'},
                            {'负责人': '  '}, {'验证方式': '手动'}, {'预期结果': ''}):
                with self.subTest(changed=changed):
                    path.write_text(csv_text([{**record, **changed}], CATALOGUE_FIELDS))
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
