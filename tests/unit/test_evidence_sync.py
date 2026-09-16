"""Review drift must not silently become fresh evidence or change business results."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from support import ROOT
from qa_workflow.evidence import file_hash, review
from qa_workflow.generation import generate, context


class EvidenceSyncTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.story = 'ISOP-2032'
        self.folder = self.root / 'requirements' / self.story
        self.folder.mkdir(parents=True)
        self.data = json.loads((ROOT / 'requirements' / self.story / 'evidence-sync.json').read_text())
        for name in self.data['files']:
            path = self.folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / 'requirements' / self.story / name).read_bytes())
        self.save()

    def save(self):
        (self.folder / 'evidence-sync.json').write_text(json.dumps(self.data))

    def test_partial_review_is_not_business_pass(self):
        result = review(self.root, self.story)
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertFalse(result['errors'])
        self.assertTrue(result['pending'])

    def test_changed_execution_blocker_stops_ai_before_call(self):
        path = self.folder / 'api/cases.json'
        path.write_text(path.read_text().replace('派发前配置变更正常生效', '批次幂等与恢复'))
        self.assertEqual(review(self.root, self.story)['status'], 'STALE')
        analyzer = Mock()
        with self.assertRaisesRegex(ValueError, '证据同步基线已失效'):
            generate(SimpleNamespace(root=self.root), self.story, {}, analyzer=analyzer)
        analyzer.assert_not_called()

    def test_unknown_case_or_source_rejected(self):
        original = copy.deepcopy(self.data)
        for field, value in [('case_ids', ['ISOP-2032-C999']), ('source_ids', ['invented'])]:
            self.data = copy.deepcopy(original)
            self.data['changes'][0][field] = value
            self.save()
            self.assertEqual(review(self.root, self.story)['status'], 'INVALID')

    def test_execution_source_cannot_be_omitted(self):
        del self.data['files']['api/cases.json']
        self.save()
        self.assertEqual(review(self.root, self.story)['status'], 'INVALID')

    def test_context_includes_decisions_and_legacy_execution(self):
        sources = context(self.root, self.story)['sources']
        self.assertTrue({'evidence-sync.md', 'evidence-sync.json', 'api/cases.json'} <= sources.keys())

    def test_missing_review_is_explicit_and_newline_independent(self):
        (self.folder / 'evidence-sync.json').unlink()
        self.assertEqual(review(self.root, self.story)['status'], 'UNREVIEWED')
        path = self.folder / 'design.md'
        before = file_hash(path)
        path.write_bytes(path.read_bytes().replace(b'\n', b'\r\n'))
        self.assertEqual(file_hash(path), before)

    def test_path_escape_and_malformed_data_rejected(self):
        self.data['files']['../outside'] = 'a' * 64
        self.save()
        self.assertEqual(review(self.root, self.story)['status'], 'INVALID')
        (self.folder / 'evidence-sync.json').write_text('[]')
        self.assertEqual(review(self.root, self.story)['status'], 'INVALID')


if __name__ == '__main__':
    unittest.main()
