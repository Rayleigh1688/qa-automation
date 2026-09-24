"""Human cards keep acceptance IDs, metadata and execution consumers compatible."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import support  # Add the repository scripts to the test import path.
from filbet import requirement_api
from qa_core.case_catalogue import export_catalogues, overview_rows
from qa_core.case_design import DESIGN_FIELDS, design_case_ids, design_rows
from qa_core.case_report import CATALOGUE_FIELDS, FIELDS, join_results, load_cases
from qa_delivery import pipeline
from qa_workflow.evidence import file_hash, review
from qa_workflow.generation import context


def cards(*items):
    """Fixture tuples: case suffix, title, state, owner, verification method."""
    lines = ['# 需求用例', '<!-- case-cards:v1 -->', '## 用例清单',
             '| 编号 | 用例名称 | 状态 | 负责人 |', '| --- | --- | --- | --- |']
    lines += [f'| ISOP-1-{key} | [{name}](#{key.lower()}) | {state} | {owner} |'
              for key, name, state, owner, method in items]
    lines += ['', '## 用例详情']
    for key, name, state, owner, method in items:
        lines += ['', f'<a id="{key.lower()}"></a>', f'### ISOP-1-{key}：{name}',
                  '', '**前置条件：**', '- 已准备独立记录。', '- 对照[C09](api/test-cases.md#c09)。',
                  '', '**操作步骤：**', '1. 打开页面。', '2. 对照记录核对结果。',
                  '', '**预期结果：**', '- 金额与独立记录一致。', '- 不改变原始记录。',
                  '', '**待确认：**', '[Q-01](questions.md#q-01)确认口径']
    lines += ['', '## 验收关联', '| 编号 | 优先级/验收点 | 方式 |', '| --- | --- | --- |']
    lines += [f'| ISOP-1-{key} | P1/AC-01 | {method} |' for key, _, _, _, method in items]
    return '\n'.join(lines + ['', '<!-- /case-cards -->', '', '## 历史', '| ISOP-1-C99 | 旧记录 |'])


class CaseDesignTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / 'requirements/ISOP-1'
        (self.folder / 'api').mkdir(parents=True)
        self.path = self.folder / 'test-cases.md'
        self.main = cards(('C01', '查看金额', 'PASS', 'Davinci', 'UI+API'),
                          ('C02', '展开说明', 'BLOCKED', '待分派', 'UI'))
        self.api = cards(('C09', '派发对账', 'NOT_RUN', '待分派', 'API+DB只读'))
        self.path.write_text(self.main, encoding='utf-8')
        (self.folder / 'api/test-cases.md').write_text(self.api, encoding='utf-8')

    def test_cards_aggregate_api_and_preserve_multiline_fields_without_history(self):
        rows = design_rows(self.path, 'ISOP-1')
        self.assertEqual([r['Case ID'] for r in rows], ['ISOP-1-C01', 'ISOP-1-C02', 'ISOP-1-C09'])
        self.assertTrue(all(set(row) == set(DESIGN_FIELDS) for row in rows))
        self.assertEqual(rows[0]['场景'], '查看金额')
        self.assertEqual((rows[0]['状态'], rows[0]['负责人']), ('PASS', 'Davinci'))
        self.assertEqual(rows[0]['操作步骤'], '1. 打开页面。\n2. 对照记录核对结果。')
        self.assertIn('- 不改变原始记录。', rows[0]['预期结果及副作用检查'])
        self.assertEqual(design_case_ids(self.path, 'ISOP-1'), {r['Case ID'] for r in rows})

    def test_export_orders_layers_preserves_states_and_does_not_invent_api_assets(self):
        rows = design_rows(self.path, 'ISOP-1')
        unordered = [rows[2], rows[1], rows[0]]
        self.assertEqual([r['用例编号'] for r in overview_rows(unordered, 'ISOP-1')],
                         ['ISOP-1-C02', 'ISOP-1-C01', 'ISOP-1-C09'])
        self.assertEqual(export_catalogues(self.folder), (3, None))
        path = self.folder / 'cases.csv'
        self.assertTrue(path.read_bytes().startswith(b'\xef\xbb\xbf'))
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            self.assertEqual(reader.fieldnames, CATALOGUE_FIELDS)
            catalogue = list(reader)
        self.assertEqual([r['类型'] for r in catalogue], ['功能', '功能', 'API'])
        self.assertEqual([r['状态'] for r in catalogue], ['PASS', 'BLOCKED', 'NOT_RUN'])
        self.assertEqual(catalogue[0]['负责人'], 'Davinci')
        self.assertNotIn('test-cases.md#', catalogue[0]['前置条件'])
        self.assertNotIn('questions.md#', catalogue[0]['前置条件'])
        self.assertIn('依赖：Q-01确认口径', catalogue[0]['前置条件'])
        self.assertIn('对照C09。', catalogue[0]['前置条件'])
        loaded = load_cases(path)
        self.assertTrue(all(set(row) == set(FIELDS) for row in loaded))
        self.assertEqual([r['类型'] for r in loaded], ['FLOW', 'UI', 'API'])
        self.assertEqual([r['执行结果'] for r in join_results(loaded, {'results': []})], ['NOT_RUN'] * 3)
        self.assertFalse((self.folder / 'api/data-cases.csv').exists())

    def test_invalid_cards_fail_before_replacing_csv(self):
        marker = self.folder / 'cases.csv'
        marker.write_text('existing catalogue')
        invalid = [
            self.main.replace('**预期结果：**', '**漏填预期：**', 1),
            self.main.replace('[查看金额](#c01)', '[不同名称](#c01)', 1),
            self.main.replace('[查看金额](#c01)', '[查看金额](#c99)', 1),
            self.main.replace('<a id="c01"></a>', ''),
            self.main.replace('<a id="c01"></a>', '<a id="c99"></a>'),
            self.main.replace('<a id="c01"></a>', '<a id="c01"></a>\n<a id="c01"></a>'),
            self.main.replace('| PASS | Davinci |', '| UNKNOWN | Davinci |', 1),
            self.main.replace('| PASS | Davinci |', '| PASS | |', 1),
            self.main.replace('### ISOP-1-C02：', '### ISOP-1-C01：', 1),
            self.main.replace('ISOP-1-C02', 'ISOP-2-C02'),
            self.main.replace('P1/AC-01', 'P1', 1),
            self.main.replace('UI+API', '手动', 1),
            self.main.replace('<!-- /case-cards -->', ''),
            self.main + '\n<!-- case-cards:v2 -->',
        ]
        for text in invalid:
            with self.subTest(source=text[:50]):
                self.path.write_text(text, encoding='utf-8')
                with self.assertRaises(ValueError):
                    export_catalogues(self.folder)
                self.assertEqual(marker.read_text(), 'existing catalogue')
                self.assertFalse((self.folder / 'api/data-cases.csv').exists())

    def test_execution_combinations_link_to_api_case_without_expanding_total(self):
        plan = {'requirement': 'ISOP-1', 'cases': [{'id': 'amount', 'datasets': ['low', 'high']}]}
        review_row = dict(zip(FIELDS, ['unused', 'API', '/example', '核对金额', '独立记录',
                                      '查询金额', '符合口径', 'P1', 'C09']))
        executions = [{'id': 'amount:' + name, 'review': {**review_row, '用例编号': 'amount:' + name},
                       'variables': {'amount': amount}, 'steps': [{'action': 'call'}]}
                      for name, amount in [('low', 1), ('high', 9)]]
        self.assertEqual(export_catalogues(self.folder, plan=plan, cases=executions), (3, 2))
        self.assertEqual({row['用例编号'] for row in load_cases(self.folder / 'cases.csv')},
                         {'ISOP-1-C01', 'ISOP-1-C02', 'ISOP-1-C09'})
        with (self.folder / 'api/data-cases.csv').open(encoding='utf-8-sig', newline='') as stream:
            data = list(csv.DictReader(stream))
        self.assertEqual([row['执行用例编号'] for row in data], ['amount:low', 'amount:high'])
        self.assertTrue(all(row['总用例编号'] == 'ISOP-1-C09' for row in data))
        self.assertIs(type(json.loads(data[0]['输入变量'])['amount']), int)

    def test_duplicate_or_cross_story_api_cards_are_rejected(self):
        api = self.folder / 'api/test-cases.md'
        for text in (self.main, self.api.replace('ISOP-1-', 'ISOP-2-')):
            api.write_text(text, encoding='utf-8')
            for reader in (design_rows, design_case_ids):
                with self.assertRaises(ValueError):
                    reader(self.path, 'ISOP-1')

    def test_legacy_id_only_consumers_remain_supported(self):
        self.path.write_text('| ISOP-1-C01 |\n| R01 |')
        (self.folder / 'api/test-cases.md').write_text('| ISOP-1-C09 |')
        self.assertEqual(design_case_ids(self.path, 'ISOP-1'), {'ISOP-1-C01', 'R01', 'ISOP-1-C09'})

    def test_existing_consumers_see_api_acceptance_and_generation_sources(self):
        for name in ('design.md', 'questions.md'):
            (self.folder / name).write_text('# 依据\nAC-01 已确认')
        suite = {'requirement': 'ISOP-1', 'cases': [
            {'id': 'read-09', 'case_ids': ['ISOP-1-C09'], 'blocked': '缺少数据'}]}
        (self.folder / 'api/cases.json').write_text(json.dumps(suite))
        with patch.object(requirement_api, 'ROOT', self.root):
            self.assertEqual(requirement_api.load_suite('ISOP-1')[0], suite)
        with patch.object(pipeline, 'ROOT', self.root):
            texts, known = pipeline.acceptance('ISOP-1')
        self.assertIn('ISOP-1-C09', known)
        self.assertEqual(texts['api/test-cases.md'], self.api)
        sources = context(self.root, 'ISOP-1')
        self.assertIn('api/test-cases.md', sources['sources'])

    def test_evidence_baseline_requires_api_design_and_tracks_its_hash(self):
        names = ('design.md', 'questions.md', 'evidence-sync.md')
        for name in names:
            (self.folder / name).write_text('fixture')
        export_catalogues(self.folder)
        manifest = {'schema_version': 1, 'story': 'ISOP-1', 'reviewed_at': '2026-09-24', 'reviewer': 'Fixture',
            'files': {name: file_hash(self.folder / name) for name in (*names, 'test-cases.md', 'cases.csv')},
            'sources': [{'id': 'S1', 'locator': 'design.md', 'coverage': 'fixture', 'status': 'READ',
                         'checked_at': '2026-09-24', 'revision': 'fixture-v1'}],
            'changes': [{'id': 'CHANGE-1', 'source_ids': ['S1'], 'case_ids': ['ISOP-1-C09'],
                         'status': 'SYNCED', 'action': 'fixture', 'verification': '未执行'}]}
        path = self.folder / 'evidence-sync.json'
        path.write_text(json.dumps(manifest))
        self.assertEqual(review(self.root, 'ISOP-1')['status'], 'INVALID')
        manifest['files']['api/test-cases.md'] = file_hash(self.folder / 'api/test-cases.md')
        path.write_text(json.dumps(manifest))
        self.assertEqual(review(self.root, 'ISOP-1')['status'], 'REVIEWED')
        (self.folder / 'api/test-cases.md').write_text(self.api + '\n')
        self.assertEqual(review(self.root, 'ISOP-1')['status'], 'STALE')


if __name__ == '__main__':
    unittest.main()
