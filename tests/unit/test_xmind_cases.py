"""Offline Xmind contracts: human authored cases, frozen expectations and honest results."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from support import ROOT
from qa_core.case_report import FIELDS, csv_text, load_cases
from qa_core.xmind_archive import XmindDocument, read_xmind
from qa_core.xmind_cases import cases_to_sheets, extract_cases, fill_results, template_sheets


def topic(title, key, children=None, **extra):
    result = {'id': key, 'title': title, **extra}
    if children is not None:
        result['children'] = {'attached': children}
    return result


def human_case(key='TC-001', name='拒绝无权限查看', **extra):
    return topic(f'[{key}] {name}', f'topic-{key}', [
        topic('前置条件：普通角色已登录；独立测试记录', key + '-pre'),
        topic('操作步骤：打开指定会员详情', key + '-step'),
        topic('预期结果：拒绝访问，且会员资料不变', key + '-expect'),
    ], **extra)


def document(cases=None):
    return XmindDocument(sheets=[{
        'id': 'sheet-one', 'title': '用例设计',
        'rootTopic': topic('代理管理', 'root-one', [
            topic('会员名单', 'module-one', cases if cases is not None else [human_case()])
        ]),
    }], entries={}, format='json')


def row(key='TC-001'):
    return dict(zip(FIELDS, [key, 'UI', '代理管理 / 会员名单', '拒绝无权限查看',
        '普通角色已登录；独立测试记录', '打开指定会员详情', '拒绝访问，且会员资料不变', '中', '未关联']))


def attached(node):
    return node.get('children', {}).get('attached', [])


def related(node):
    return [child for nodes in node.get('children', {}).values() for child in nodes]


def case_topics(sheets):
    """Find fixture case titles without relying on the production extractor."""
    found = {}
    def visit(node):
        if node.get('title', '').startswith('[TC-'):
            found[node['title'].split(']', 1)[0][1:]] = node
        for values in node.get('children', {}).values():
            for child in values:
                visit(child)
    for sheet in sheets:
        visit(sheet['rootTopic'])
    return found


def result_values(case_topic):
    branches = [child for child in related(case_topic) if child['title'] == '本批执行结果']
    if len(branches) != 1:
        raise AssertionError('each case needs one current-batch result branch')
    values = {}
    for child in related(branches[0]):
        label, _, value = child['title'].replace(':', '：', 1).partition('：')
        if not value and related(child):
            value = '\n'.join(item['title'] for item in related(child))
        values[label] = value
    return values


class XmindCasesTests(unittest.TestCase):
    def test_handwritten_case_gets_explicit_identity_and_parent_module(self):
        source = document()
        before = copy.deepcopy(source.sheets)
        cases, locations = extract_cases(source)
        self.assertEqual(cases, [row()])
        self.assertEqual(locations, [{'case_id': 'TC-001', 'sheet_id': 'sheet-one', 'topic_id': 'topic-TC-001'}])
        self.assertEqual(source.sheets, before)

    def test_notes_aliases_and_nested_steps_keep_author_order_and_test_data(self):
        authored = topic('[TC-002] 日期边界', 'topic-TC-002', [
            topic('前置', 'pre', notes={'plain': {'content': '指定独立样本\n记录基线'}}),
            topic('测试数据：2026-10-05、2026-10-06', 'data'),
            topic('步骤', 'steps', [
                topic('选择日期', 'step-one', [topic('确认GMT+8日切', 'step-one-detail')]),
                topic('查询列表', 'step-two'),
            ]),
            topic('预期', 'expect', notes={'plain': {'content': '只出现区间内记录\n不写入业务数据'}}),
            topic('类型：API', 'kind'), topic('级别：高', 'priority'),
            topic('验收点：C05', 'acceptance'), topic('模块/接口：GET /report/list', 'module'),
        ])
        cases, _ = extract_cases(document([authored]))
        self.assertEqual(cases, [dict(zip(FIELDS, ['TC-002', 'API', 'GET /report/list', '日期边界',
            '指定独立样本\n记录基线',
            '测试数据：2026-10-05、2026-10-06\n操作步骤：选择日期\n  确认GMT+8日切\n查询列表',
            '只出现区间内记录\n不写入业务数据', '高', 'C05']))])

    def test_multiple_sheets_detached_cases_and_unlabelled_function_groups(self):
        unlabelled = topic('筛选条件', 'not-a-case', [
            topic('前置条件：说明文字', 'guide-pre'),
            topic('操作步骤：说明文字', 'guide-step'),
            topic('预期结果：说明文字', 'guide-expect'),
        ])
        source = document([human_case(), unlabelled])
        source.sheets[0]['rootTopic']['children']['detached'] = [human_case('TC-002', '浮动用例')]
        source.sheets.append({'id': 'sheet-two', 'title': '独立表',
            'rootTopic': topic('代理端', 'root-two', [])})
        source.sheets[1]['rootTopic']['children']['floating'] = [human_case('TC-003', '第二张表')]
        cases, locations = extract_cases(source)
        self.assertEqual([item['用例编号'] for item in cases], ['TC-001', 'TC-002', 'TC-003'])
        self.assertEqual([item['模块/接口'] for item in cases], ['代理管理 / 会员名单', '代理管理', '代理端'])
        self.assertEqual(locations[-1], {'case_id': 'TC-003', 'sheet_id': 'sheet-two', 'topic_id': 'topic-TC-003'})

    def test_inline_notes_and_child_details_are_all_part_of_the_human_expectation(self):
        authored = topic('[TC-004] 保存人工细节', 'topic-TC-004', [
            topic('前置条件：已登录', 'pre', [
                topic('检查初态', 'pre-child', notes={'plain': {'content': '只读确认'}}),
            ], notes={'plain': {'content': '隔离样本'}}),
            topic('操作步骤：选择本轮范围', 'steps', [
                topic('查询', 'query', notes={'plain': {'content': '保存响应\n记录查询时间'}}),
                topic('核对页面', 'check-page'),
            ], notes={'plain': {'content': '界面日期采用GMT+8'}}),
            topic('预期结果：区间正确', 'expected', [
                topic('统计与源数据一致', 'expected-child', notes={'plain': {'content': '字段无泄露'}}),
            ], notes={'plain': {'content': '会员资料不变'}}),
        ])
        cases, _ = extract_cases(document([authored]))
        self.assertEqual(cases[0]['前置条件'], '已登录\n隔离样本\n检查初态\n  只读确认')
        self.assertEqual(cases[0]['参数/步骤'], '选择本轮范围\n界面日期采用GMT+8\n查询\n  保存响应\n  记录查询时间\n核对页面')
        self.assertEqual(cases[0]['预期结果'], '区间正确\n会员资料不变\n统计与源数据一致\n  字段无泄露')

    def test_ambiguous_or_incomplete_handwritten_cases_are_rejected(self):
        duplicate = document([human_case(), human_case()])
        other_sheet = document()
        other_sheet.sheets.append({'id': 'sheet-two', 'rootTopic': topic('另一表', 'root-two', [human_case()])})
        aliased = human_case()
        attached(aliased).append(topic('预期：另一个预期', 'duplicate-expect'))
        malformed = [duplicate, other_sheet, document([aliased])]
        for missing in range(3):
            incomplete = human_case()
            attached(incomplete).pop(missing)
            malformed.append(document([incomplete]))
        for source in malformed:
            with self.subTest(source=source.sheets):
                with self.assertRaises(ValueError):
                    extract_cases(source)

    def test_unnumbered_function_groups_may_have_repeated_guidance_fields(self):
        grouping = topic('两个正常路径', 'guidance-group', [
            topic('预期结果：页面说明', 'guidance-expect-one'),
            topic('预期：接口说明', 'guidance-expect-two'),
            human_case(),
        ])
        cases, _ = extract_cases(document([grouping]))
        self.assertEqual(cases, [{**row(), '模块/接口': '代理管理 / 会员名单 / 两个正常路径'}])

    def test_test_data_cannot_stand_in_for_required_operation_steps(self):
        authored = human_case()
        attached(authored)[1] = topic('测试数据：已脱敏的独立样本', 'data-without-steps')
        with self.assertRaises(ValueError):
            extract_cases(document([authored]))

    def test_explicit_id_field_agrees_with_the_case_title(self):
        authored = human_case()
        attached(authored).append(topic('Case ID：TC-001', 'explicit-id'))
        self.assertEqual(extract_cases(document([authored]))[0], [row()])
        attached(authored)[-1]['title'] = 'Case ID：TC-999'
        with self.assertRaises(ValueError):
            extract_cases(document([authored]))

    def test_template_uses_rightward_structure_and_is_importable_as_unexecuted_cases(self):
        sheets = template_sheets(title='人工首稿')
        self.assertEqual(sheets[0]['rootTopic']['title'], '人工首稿')
        self.assertEqual(sheets[0]['rootTopic']['structureClass'], 'org.xmind.ui.logic.right')
        cases, _ = extract_cases(XmindDocument(sheets=sheets, entries={}, format='json'))
        self.assertTrue(cases)
        filled = fill_results(XmindDocument(sheets=sheets, entries={}, format='json'), {'results': []})
        self.assertTrue(all(result_values(item)['执行结果'] == 'NOT_RUN' for item in case_topics(filled).values()))

    def test_numbered_group_titles_do_not_hide_cases_or_weaken_required_fields(self):
        for title in ('W26 测试用例', '[W26] 测试用例'):
            with self.subTest(title=title):
                cases, _ = extract_cases(XmindDocument(template_sheets(title), {}, 'json'))
                self.assertEqual([item['用例编号'] for item in cases], ['TC-001', 'TC-002'])
        for module in ('P0 回归', '[P0] 回归'):
            with self.subTest(module=module):
                original = [{**row(), '模块/接口': module}]
                actual, _ = extract_cases(XmindDocument(cases_to_sheets(original), {}, 'json'))
                self.assertEqual(actual, original)
        bare = human_case()
        bare['title'] = 'TC-001 拒绝无权限查看'
        self.assertEqual(extract_cases(document([bare]))[0], [row()])
        for title in ('[TC-002] 缺少字段', 'TC-002 缺少字段'):
            incomplete = human_case('TC-002')
            incomplete['title'] = title
            attached(incomplete).pop()
            with self.subTest(incomplete_title=title), self.assertRaises(ValueError):
                extract_cases(document([human_case(), incomplete]))
        empty = topic('[TC-002] 空用例', 'empty-case')
        with self.assertRaises(ValueError):
            extract_cases(document([human_case(), empty]))

    def test_csv_export_and_import_preserve_every_frozen_execution_field(self):
        rows = [row(), {**row('TC-002'), '类型': 'FLOW', '用例名称': '跨端完整流程',
            '前置条件': '指定样本\n并发前先查重', '参数/步骤': '1. 查询\n2. 人工核页面',
            '预期结果': '显示逗号,引号“值”\n状态一致', '模块/接口': '钱包 / 交易', '级别': '冒烟', '验收点': 'C01,C02'}]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'cases.csv'
            path.write_text(csv_text(rows, FIELDS), encoding='utf-8')
            frozen = load_cases(path)
        self.assertEqual(frozen, rows)
        sheets = cases_to_sheets(frozen, title='CSV原稿')
        self.assertEqual(sheets[0]['rootTopic']['structureClass'], 'org.xmind.ui.logic.right')
        actual, _ = extract_cases(XmindDocument(sheets=sheets, entries={}, format='json'))
        self.assertEqual(actual, rows)

    def test_fill_results_uses_exact_ids_preserves_source_and_does_not_reuse_old_pass(self):
        first = human_case('TC-001')
        first['notes'] = {'plain': {'content': '人工补充，原样保留'}}
        first['markers'] = [{'markerId': 'priority-1'}]
        unknown = topic('额外观察', 'unknown', [topic('无需自动识别此内容', 'unknown-detail')],
            hyperlink='resources/manual.txt')
        attached(first).append(unknown)
        second = human_case('TC-010', '已有旧结果的用例')
        attached(second).append(topic('执行结果：PASS', 'old-result'))
        manual_batch_note = topic('执行补充：保留人工观察', 'manual-batch-note',
            notes={'plain': {'content': '旧结果更新时不丢失这一条'}})
        attached(second).append(topic('本批执行结果', 'old-batch', [
            topic('执行结果', 'old-batch-status', [topic('PASS', 'old-batch-status-value')]),
            topic('证据', 'old-batch-proof', [topic('old.json', 'old-batch-proof-value')]), manual_batch_note]))
        source = document([first, second])
        original = copy.deepcopy(source.sheets)
        report = {'results': [{'id': 'TC-001', 'status': 'FAIL', 'actual': '普通角色看到了隐私字段',
            'category': '产品缺陷', 'evidence': 'source/TC-001.png'}]}
        sheets = fill_results(source, report)
        self.assertEqual(source.sheets, original)
        self.assertIsNot(sheets, source.sheets)
        mapped = case_topics(sheets)
        self.assertEqual(mapped['TC-001']['notes'], first['notes'])
        self.assertEqual(mapped['TC-001']['markers'], first['markers'])
        self.assertIn(unknown, attached(mapped['TC-001']))
        first_result = result_values(mapped['TC-001'])
        self.assertEqual({field: first_result[field] for field in ['执行结果', '实际结果', '分类', '证据']},
            {'执行结果': 'FAIL', '实际结果': '普通角色看到了隐私字段',
            '分类': '产品缺陷', '证据': 'source/TC-001.png'})
        pending = result_values(mapped['TC-010'])
        self.assertEqual(pending['执行结果'], 'NOT_RUN')
        self.assertEqual(pending['实际结果'], '本批次未执行')
        self.assertIn(topic('执行结果：PASS', 'old-result'), attached(mapped['TC-010']))
        updated_branch = next(item for item in attached(mapped['TC-010']) if item['title'] == '本批执行结果')
        self.assertIn(manual_batch_note, attached(updated_branch))
        self.assertEqual(extract_cases(XmindDocument(sheets=sheets, entries={}, format='json'))[0], [row(), {**row('TC-010'), '用例名称': '已有旧结果的用例'}])

    def test_fill_results_rejects_wrong_ids_duplicates_and_unsupported_passes(self):
        good = {'id': 'TC-001', 'status': 'PASS', 'actual': '独立本地夹具结果', 'evidence': 'fixture.png'}
        bad = [
            [{**good, 'id': 'TC-01'}], [good, good], [{**good, 'evidence': ''}],
            [{**good, 'evidence': '   '}],
            [{**good, 'actual': ''}], [{**good, 'status': 'DONE'}],
        ]
        for records in bad:
            with self.subTest(records=records):
                source = document()
                original = copy.deepcopy(source.sheets)
                with self.assertRaises(ValueError):
                    fill_results(source, {'results': records})
                self.assertEqual(source.sheets, original)

    def test_handwritten_old_result_fields_are_updated_without_contradictory_pass(self):
        authored = human_case()
        attached(authored).append(topic('本批执行结果', 'old-batch', [
            topic('执行结果：PASS', 'old-status'), topic('证据：old.png', 'old-proof')]))
        sheets = fill_results(document([authored]), {'results': []})
        current = case_topics(sheets)['TC-001']
        values = result_values(current)
        self.assertEqual(values['执行结果'], 'NOT_RUN')
        self.assertNotIn('PASS', values.values())
        branch = next(item for item in attached(current) if item['title'] == '本批执行结果')
        self.assertEqual(sum(item['title'] == '执行结果' for item in attached(branch)), 1)

    def test_fill_results_checks_all_frozen_fields_before_changing_a_map(self):
        frozen = [row()]
        source = document()
        filled = fill_results(source, {'results': []}, cases=frozen)
        self.assertEqual(extract_cases(XmindDocument(sheets=filled, entries={}, format='json'))[0], frozen)
        self.assertEqual(result_values(case_topics(filled)['TC-001'])['执行结果'], 'NOT_RUN')
        for field in FIELDS:
            changed = copy.deepcopy(frozen)
            changed[0][field] = 'API' if field == '类型' else ('TC-999' if field == '用例编号' else '人工修改后的值')
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    fill_results(source, {'results': []}, cases=changed)

    def test_frozen_csv_formula_guards_do_not_change_original_text_or_strip_literal_quotes(self):
        rows = [{**row(), '模块/接口': '@ 模块', '前置条件': '  + 只读样本',
                 '参数/步骤': '- 查询列表', '预期结果': '= 0', '用例名称': "'- 原始引号"}]
        source = XmindDocument(cases_to_sheets(rows), {}, 'json')
        original = copy.deepcopy(source.sheets)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'frozen.csv'
            path.write_text(csv_text(rows, FIELDS), encoding='utf-8')
            encoded = load_cases(path)
        self.assertEqual(encoded[0]['参数/步骤'], "'- 查询列表")
        self.assertEqual(encoded[0]['预期结果'], "'= 0")
        self.assertEqual(encoded[0]['用例名称'], "'- 原始引号")
        for frozen in (rows, encoded):
            filled = fill_results(source, {'results': []}, cases=frozen)
            self.assertEqual(extract_cases(XmindDocument(filled, {}, 'json'))[0], rows)
        changed = copy.deepcopy(encoded)
        changed[0]['用例名称'] = '- 原始引号'
        with self.assertRaises(ValueError):
            fill_results(source, {'results': []}, cases=changed)
        changed = copy.deepcopy(encoded)
        changed[0]['参数/步骤'] = "''- 查询列表"
        with self.assertRaises(ValueError):
            fill_results(source, {'results': []}, cases=changed)
        self.assertEqual(source.sheets, original)

    def test_moved_result_branch_fields_and_values_update_in_their_original_relationships(self):
        for branch_group, field_group, value_group in [
            ('detached', 'floating', 'detached'), ('floating', 'detached', 'floating'),
            ('custom', 'custom', 'custom'),
        ]:
            with self.subTest(groups=(branch_group, field_group, value_group)):
                authored = human_case()
                value = topic('PASS', 'old-status-value', labels=['保留标签'])
                field = topic('执行结果', 'old-status', [])
                field['children'][value_group] = [value]
                observation = topic('人工观察', 'custom-observation', notes={'plain': {'content': '保留说明'}})
                branch = topic('本批执行结果', 'old-batch', [observation],
                               notes={'plain': {'content': '保留分支备注'}})
                branch['children'][field_group] = [field]
                authored['children'][branch_group] = [branch]
                source = document([authored])
                original = copy.deepcopy(source.sheets)
                filled = fill_results(source, {'results': []})
                current = case_topics(filled)['TC-001']
                self.assertEqual(result_values(current)['执行结果'], 'NOT_RUN')
                branches = [node for node in related(current) if node['title'] == '本批执行结果']
                self.assertEqual(len(branches), 1)
                updated = current['children'][branch_group][0]
                status = updated['children'][field_group][0]
                self.assertEqual(status['children'][value_group][0], {**value, 'title': 'NOT_RUN'})
                self.assertEqual(updated['notes'], branch['notes'])
                self.assertIn(observation, related(updated))
                self.assertEqual(source.sheets, original)

    def test_ambiguous_result_values_or_notes_fail_without_mutating_the_map(self):
        records = []
        for field_notes, value_notes in [
            ({'plain': {'content': 'PASS'}}, {}), ({}, {'plain': {'content': '旧PASS说明'}}),
            ({'rich': {'content': '<p>PASS</p>'}}, {}),
        ]:
            field = topic('执行结果', 'old-status', [topic('PASS', 'old-status-value', notes=value_notes)], notes=field_notes)
            records.append(topic('本批执行结果', 'old-batch', [field]))
        multiple = topic('执行结果', 'old-status', [topic('PASS', 'old-status-value')])
        multiple['children']['detached'] = [topic('旧结果', 'extra-value')]
        records.append(topic('本批执行结果', 'old-batch', [multiple]))
        duplicate_field = topic('本批执行结果', 'old-batch', [topic('执行结果：PASS', 'old-status')])
        duplicate_field['children']['floating'] = [topic('执行结果：FAIL', 'duplicate-status')]
        records.append(duplicate_field)
        for branch in records:
            authored = human_case()
            attached(authored).append(branch)
            source = document([authored])
            original = copy.deepcopy(source.sheets)
            with self.subTest(branch=branch), self.assertRaises(ValueError):
                fill_results(source, {'results': []})
            self.assertEqual(source.sheets, original)
        authored = human_case()
        attached(authored).append(topic('本批执行结果', 'batch-one'))
        authored['children']['detached'] = [topic('本批执行结果', 'batch-two')]
        source = document([authored])
        original = copy.deepcopy(source.sheets)
        with self.assertRaises(ValueError):
            fill_results(source, {'results': []})
        self.assertEqual(source.sheets, original)


class XmindCliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/xmind-test-cases.py'), *map(str, args)],
            cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)

    def assert_cli_ok(self, *args):
        result = self.run_cli(*args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_offline_export_import_and_result_fill_without_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            cases_path = temp / 'cases.csv'
            cases_path.write_text(csv_text([row(), row('TC-002')], FIELDS), encoding='utf-8')
            map_path = temp / 'authored.xmind'
            self.assert_cli_ok('export', '--cases', cases_path, '--out', map_path)
            original = map_path.read_bytes()
            imported = temp / 'imported'
            self.assert_cli_ok('import', '--input', map_path, '--out', imported)
            self.assertTrue({'cases.csv', 'cases.json', 'source.json', 'README.md'} <= {p.name for p in imported.iterdir()})
            self.assertEqual(load_cases(imported / 'cases.csv'), [row(), row('TC-002')])
            self.assertEqual(json.loads((imported / 'cases.json').read_text()), [row(), row('TC-002')])
            manifest = json.loads((imported / 'source.json').read_text())
            self.assertEqual(manifest['source_sha256'], hashlib.sha256(original).hexdigest())
            self.assertEqual(manifest['case_count'], 2)
            self.assertEqual({item['case_id'] for item in manifest['locations']}, {'TC-001', 'TC-002'})
            report = temp / 'result.json'
            report.write_text(json.dumps({'results': [{'id': 'TC-001', 'status': 'PASS',
                'actual': '本地假数据，未登录系统', 'evidence': 'fixture.png'}]}, ensure_ascii=False), encoding='utf-8')
            filled = temp / 'filled.xmind'
            self.assert_cli_ok('fill-results', '--input', map_path, '--results', report,
                '--cases', imported / 'cases.json', '--out', filled)
            mapped = case_topics(read_xmind(filled).sheets)
            self.assertEqual(result_values(mapped['TC-001'])['执行结果'], 'PASS')
            self.assertEqual(result_values(mapped['TC-002'])['执行结果'], 'NOT_RUN')
            self.assertEqual(map_path.read_bytes(), original)
            for args, existing in [
                (('export', '--cases', cases_path, '--out', map_path), map_path),
                (('import', '--input', map_path, '--out', imported), imported / 'cases.json'),
                (('fill-results', '--input', map_path, '--results', report, '--out', filled), filled),
            ]:
                before = existing.read_bytes()
                rejected = self.run_cli(*args)
                self.assertNotEqual(rejected.returncode, 0, rejected.stdout + rejected.stderr)
                self.assertEqual(existing.read_bytes(), before)

    def test_template_and_invalid_input_leave_existing_or_new_outputs_safe(self):
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            template = temp / 'template.xmind'
            self.assert_cli_ok('template', '--out', template)
            original = template.read_bytes()
            self.assertNotEqual(self.run_cli('template', '--out', template).returncode, 0)
            self.assertEqual(template.read_bytes(), original)
            source = temp / 'invalid.csv'
            source.write_text(csv_text([{**row(), '预期结果': ''}], FIELDS), encoding='utf-8')
            target = temp / 'invalid.xmind'
            self.assertNotEqual(self.run_cli('export', '--cases', source, '--out', target).returncode, 0)
            self.assertFalse(target.exists())

    def test_imported_guarded_csv_can_freeze_results_without_changing_human_definition(self):
        rows = [{**row(), '参数/步骤': '- 查询列表', '预期结果': '= 0'}]
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            definitions = temp / 'source.json'
            definitions.write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
            source = temp / 'source.xmind'
            self.assert_cli_ok('export', '--cases', definitions, '--out', source, '--title', '[W26] 测试用例')
            original = source.read_bytes()
            imported = temp / 'imported'
            self.assert_cli_ok('import', '--input', source, '--out', imported)
            self.assertEqual(json.loads((imported / 'cases.json').read_text()), rows)
            self.assertEqual(load_cases(imported / 'cases.csv')[0]['参数/步骤'], "'- 查询列表")
            results = temp / 'results.json'
            results.write_text('{"results": []}', encoding='utf-8')
            target = temp / 'filled.xmind'
            self.assert_cli_ok('fill-results', '--input', source, '--results', results,
                               '--cases', imported / 'cases.csv', '--out', target)
            self.assertEqual(extract_cases(read_xmind(target))[0], rows)
            self.assertEqual(source.read_bytes(), original)

    def test_classic_xml_case_can_be_imported_and_filled_with_resources_preserved(self):
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
<xmap-content xmlns="urn:xmind:xmap:xmlns:content:2.0" xmlns:proof="urn:offline-proof" version="2.0">
  <sheet id="classic-sheet"><title>经典用例</title>
    <topic id="classic-root"><title>代理管理</title><children><topics type="attached">
      <topic id="classic-module"><title>会员名单</title><children><topics type="attached">
        <topic id="classic-case" proof:keep="human"><title>[TC-001] 拒绝无权限查看</title>
          <proof:annotation>保留人工补充</proof:annotation><children><topics type="attached">
            <topic id="classic-pre"><title>前置条件：普通角色已登录；独立测试记录</title></topic>
            <topic id="classic-step"><title>操作步骤：打开指定会员详情</title></topic>
            <topic id="classic-expect"><title>预期结果：拒绝访问，且会员资料不变</title></topic>
          </topics></children>
        </topic>
      </topics></children></topic>
    </topics></children></topic>
  </sheet>
</xmap-content>'''
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            source = temp / 'classic.xmind'
            resource = b'offline human attachment; retain bytes'
            with zipfile.ZipFile(source, 'w') as archive:
                archive.writestr('content.xml', xml)
                archive.writestr('resources/manual.txt', resource)
            original = source.read_bytes()
            imported = temp / 'classic-import'
            self.assert_cli_ok('import', '--input', source, '--out', imported)
            self.assertEqual(load_cases(imported / 'cases.csv'), [row()])
            report = temp / 'classic-result.json'
            report.write_text(json.dumps({'results': [{'id': 'TC-001', 'status': 'FAIL',
                'actual': '仅本地fixture观察', 'evidence': 'fixture.json'}]}, ensure_ascii=False), encoding='utf-8')
            filled = temp / 'classic-filled.xmind'
            self.assert_cli_ok('fill-results', '--input', source, '--results', report,
                '--cases', imported / 'cases.csv', '--out', filled)
            self.assertEqual(source.read_bytes(), original)
            document = read_xmind(filled)
            self.assertEqual(document.format, 'xml')
            self.assertEqual(document.entries['resources/manual.txt'], resource)
            self.assertNotIn('content.json', document.entries)
            self.assertIn(b'proof:keep="human"', document.entries['content.xml'])
            self.assertIn('保留人工补充', document.entries['content.xml'].decode('utf-8'))
            self.assertEqual(extract_cases(document)[0], [row()])
            self.assertEqual(result_values(case_topics(document.sheets)['TC-001'])['执行结果'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
