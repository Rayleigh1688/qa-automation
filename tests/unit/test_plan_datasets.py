import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from support import ROOT
from requirement_paths import requirement_dir
from qa_core.case_report import FIELDS
from qa_core.execution_plan import load, resolve
from qa_workflow.evidence import file_hash, review
from qa_workflow.generation import context


HAS_PYYAML = importlib.util.find_spec('yaml') is not None


class PlanDatasetTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.story = 'ISOP-2032'
        self.directory = self.root / 'requirements' / self.story
        self.directory.mkdir(parents=True)
        self.path = self.directory / 'plan.json'
        self.source = self.directory / 'api' / 'datasets.yaml'
        self.source.parent.mkdir()
        self.source.write_text('advertisement:\n  ad_id: "001"\n', encoding='utf-8')
        case_review = dict.fromkeys(FIELDS, '示例')
        case_review.update(用例编号='TEST-001', 类型='API', 验收点='A01')
        self.plan = {
            'schema_version': 2,
            'requirement': self.story,
            'acceptance_ids': ['A01'],
            'datasets_file': 'api/datasets.yaml',
            'services': {'client': {'env': 'API_URL'}},
            'actors': {'anonymous': {'services': ['client']}},
            'contracts': {'detail': {'service': 'client', 'method': 'GET',
                                     'path': '/member/buriedPoint/detailV2', 'encoding': 'cbor', 'write': False}},
            'cases': [{
                'id': 'TEST-001', 'review': case_review, 'datasets': ['advertisement'],
                'steps': [{'id': 'detail', 'actor': 'anonymous', 'action': 'api',
                           'contract': 'detail', 'auth': 'missing', 'query': {'ad_id': '${data.ad_id}'},
                           'expect': [{'path': 'http', 'op': 'eq', 'value': 200},
                                      {'path': 'body.status', 'op': 'eq', 'value': True}]}],
            }],
        }
        self.save_plan()

    def save_plan(self):
        self.path.write_text(json.dumps(self.plan, ensure_ascii=False), encoding='utf-8')

    def separate_cases(self, *, inline_datasets=True):
        if inline_datasets:
            del self.plan['datasets_file']
            self.plan['datasets'] = {'advertisement': {'ad_id': '001'}}
        filename = 'api/plan-cases.json'
        fragment = {key: self.plan.pop(key) for key in ('contracts', 'cases')}
        self.plan['cases_file'] = filename
        source = self.directory / filename
        source.write_text(json.dumps(fragment, ensure_ascii=False), encoding='utf-8')
        self.save_plan()
        return source, fragment

    def evidence_manifest(self):
        historical = requirement_dir(ROOT, self.story)
        manifest = json.loads((historical / 'evidence-sync.json').read_bytes())
        for name in manifest['files']:
            path = self.directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((historical / name).read_bytes())
        manifest['files']['plan.json'] = file_hash(self.path)
        return manifest

    def test_json_only_keeps_the_original_hash_without_yaml_installed(self):
        del self.plan['datasets_file']
        self.plan['datasets'] = {'advertisement': {'ad_id': '001'}}
        self.save_plan()
        with patch.dict(sys.modules, {'yaml': None}):
            plan, cases, digest = load(self.path)
        self.assertEqual(plan, self.plan)
        self.assertEqual(cases[0]['id'], 'TEST-001:advertisement')
        self.assertEqual(digest, hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_missing_pyyaml_has_an_explicit_offline_error(self):
        with patch.dict(sys.modules, {'yaml': None}):
            with self.assertRaisesRegex(ValueError, 'require PyYAML .*requirements-yaml.txt'):
                load(self.path)

    @unittest.skipUnless(HAS_PYYAML, 'optional PyYAML is not installed')
    def test_yaml_dataset_expands_and_binds_the_plan_hash_to_source_bytes(self):
        yaml_text = 'advertisement:\n  ad_id: "001"\n  nested: [true, null, 9223372036854775807]\n'
        self.source.write_text(yaml_text, encoding='utf-8')
        plan, cases, first = load(self.path)
        self.assertEqual(plan['datasets']['advertisement']['nested'], [True, None, 9223372036854775807])
        case = cases[0]
        self.assertEqual(case['id'], 'TEST-001:advertisement')
        self.assertEqual(resolve(case['steps'][0]['query'], case['variables']), {'ad_id': '001'})
        self.source.write_text(yaml_text + '# audit change to the source bytes\n', encoding='utf-8')
        _, unchanged_cases, second = load(self.path)
        self.assertEqual(unchanged_cases, cases)
        self.assertNotEqual(first, second)

    @unittest.skipUnless(HAS_PYYAML, 'optional PyYAML is not installed')
    def test_yaml_rejects_duplicate_keys_and_invalid_values(self):
        examples = [
            ('advertisement: {}\nadvertisement: {}', 'duplicate'),
            ('advertisement: {ad_id: 1, ad_id: 2}', 'duplicate'),
            ('advertisement: {1: true}', 'keys must be strings'),
            ('advertisement: []', 'map dataset names to objects'),
            ('advertisement: {ad_id: 2026-11-27}', 'JSON-compatible'),
            ('advertisement: {ad_id: .nan}', 'JSON-compatible'),
            ('advertisement: {ad_id: !!python/tuple [1]}', 'syntax or tag'),
            ('advertisement: {ad_id: &items [*items]}', 'aliases'),
        ]
        for content, message in examples:
            with self.subTest(content=content):
                self.source.write_text(content, encoding='utf-8')
                with self.assertRaisesRegex(ValueError, message):
                    load(self.path)

    def test_inline_and_yaml_datasets_cannot_coexist(self):
        self.plan['datasets'] = {}
        self.save_plan()
        with self.assertRaisesRegex(ValueError, 'mutually exclusive'):
            load(self.path)

    def test_datasets_file_must_be_a_relative_yaml_path(self):
        for candidate in ('../datasets.yaml', '/tmp/datasets.yaml', 'C:/tmp/datasets.yaml', 'api/data.csv', None):
            with self.subTest(candidate=candidate):
                self.plan['datasets_file'] = candidate
                self.save_plan()
                with self.assertRaisesRegex(ValueError, 'relative .yaml or .yml path'):
                    load(self.path)

    def test_datasets_file_cannot_use_a_symlink_outside_the_requirement(self):
        external = self.root / 'external.yml'
        external.write_bytes(self.source.read_bytes())
        link = self.source.with_name('linked.yml')
        try:
            link.symlink_to(external)
        except OSError:
            self.skipTest('symlinks are unavailable on this system')
        self.plan['datasets_file'] = 'api/linked.yml'
        self.save_plan()
        with self.assertRaisesRegex(ValueError, 'within the requirement directory'):
            load(self.path)

    def test_evidence_and_draft_context_track_the_referenced_yaml_source(self):
        manifest = self.evidence_manifest()
        manifest_path = self.directory / 'evidence-sync.json'
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        self.assertEqual(review(self.root, self.story)['status'], 'INVALID')

        source_name = self.plan['datasets_file']
        manifest['files'][source_name] = file_hash(self.source)
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        self.assertEqual(review(self.root, self.story)['status'], 'PARTIAL')
        before = context(self.root, self.story)['sources'][source_name]
        self.source.write_text('advertisement:\n  ad_id: "002"\n', encoding='utf-8')
        self.assertEqual(review(self.root, self.story)['status'], 'STALE')
        after = context(self.root, self.story)['sources'][source_name]
        self.assertNotEqual(before['sha256'], after['sha256'])

    def test_cases_file_is_inlined_in_the_snapshot_and_changes_the_plan_digest(self):
        source, fragment = self.separate_cases()
        with patch.dict(sys.modules, {'yaml': None}):
            plan, cases, first = load(self.path)
            self.assertNotIn('cases_file', plan)
            self.assertEqual(plan['contracts'], fragment['contracts'])
            self.assertEqual(plan['cases'], fragment['cases'])
            self.assertEqual(cases[0]['id'], 'TEST-001:advertisement')
            source.write_bytes(source.read_bytes() + b'\n')
            unchanged_plan, unchanged_cases, second = load(self.path)
        self.assertEqual(unchanged_plan, plan)
        self.assertEqual(unchanged_cases, cases)
        self.assertNotEqual(first, second)

    @unittest.skipUnless(HAS_PYYAML, 'optional PyYAML is not installed')
    def test_cases_file_and_yaml_dataset_are_bound_to_the_same_validated_plan(self):
        self.separate_cases(inline_datasets=False)
        plan, cases, first = load(self.path)
        self.assertNotIn('cases_file', plan)
        self.assertNotIn('datasets_file', plan)
        self.assertEqual(cases[0]['variables']['data']['ad_id'], '001')
        self.source.write_text('advertisement:\n  ad_id: "002"\n', encoding='utf-8')
        _, changed_cases, second = load(self.path)
        self.assertEqual(changed_cases[0]['variables']['data']['ad_id'], '002')
        self.assertNotEqual(first, second)

    def test_cases_file_rejects_inline_definitions_and_paths_outside_requirement(self):
        _, fragment = self.separate_cases()
        for key in fragment:
            with self.subTest(inline=key):
                self.plan[key] = fragment[key]
                self.save_plan()
                with self.assertRaisesRegex(ValueError, 'mutually exclusive'):
                    load(self.path)
                del self.plan[key]
        for candidate in ('../cases.json', '/tmp/cases.json', 'C:/tmp/cases.json', 'api/cases.yaml', None):
            with self.subTest(path=candidate):
                self.plan['cases_file'] = candidate
                self.save_plan()
                with self.assertRaisesRegex(ValueError, 'relative .json path'):
                    load(self.path)

    def test_cases_file_cannot_use_a_symlink_outside_the_requirement(self):
        source, _ = self.separate_cases()
        outside = self.root / 'outside.json'
        outside.write_bytes(source.read_bytes())
        source.unlink()
        source.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'within the requirement directory'):
            load(self.path)

    def test_cases_file_rejects_other_fields_and_invalid_container_types(self):
        source, _ = self.separate_cases()
        for content in ('[]', '{"contracts":{},"cases":[],"variables":{}}', '{"contracts":[],"cases":[]}',
                        '{"contracts":{},"cases":{}}'):
            with self.subTest(content=content):
                source.write_text(content, encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'exactly a contracts object and a cases array'):
                    load(self.path)
        source.write_text('{"contracts":{},"cases":[],"cases":[]}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'duplicate JSON key'):
            load(self.path)

    def test_evidence_and_draft_context_track_the_referenced_cases_file(self):
        source, fragment = self.separate_cases()
        source_name = self.plan['cases_file']
        manifest = self.evidence_manifest()
        manifest_path = self.directory / 'evidence-sync.json'
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        self.assertEqual(review(self.root, self.story)['status'], 'INVALID')

        manifest['files'][source_name] = file_hash(source)
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        self.assertEqual(review(self.root, self.story)['status'], 'PARTIAL')
        before = context(self.root, self.story)['sources'][source_name]
        fragment['cases'][0]['review']['用例名称'] = '修改后的用例'
        source.write_text(json.dumps(fragment, ensure_ascii=False), encoding='utf-8')
        self.assertEqual(review(self.root, self.story)['status'], 'STALE')
        after = context(self.root, self.story)['sources'][source_name]
        self.assertNotEqual(before['sha256'], after['sha256'])
