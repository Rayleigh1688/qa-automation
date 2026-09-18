"""Archived requirements remain addressable but cannot enter default discovery."""
import tempfile
import unittest
from pathlib import Path
from support import ROOT
from requirement_paths import requirement_dir, requirement_dirs, is_archived
from qa_delivery.intake import requirement_catalog


class RequirementPathsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.active = self.root / 'requirements/ISOP-2100'
        self.archive = self.root / 'requirements/history/through-ISOP-2072/ISOP-2027'
        self.active.mkdir(parents=True)
        self.archive.mkdir(parents=True)

    def test_default_discovery_and_intake_exclude_history(self):
        self.assertEqual(requirement_dirs(self.root), [self.active])
        self.assertEqual(set(requirement_catalog(self.root / 'requirements')), {'ISOP-2100'})
        self.assertEqual(set(requirement_dirs(self.root, include_history=True)), {self.active, self.archive})

    def test_explicit_id_resolves_history_and_missing_current(self):
        self.assertEqual(requirement_dir(self.root, 'ISOP-2027'), self.archive)
        self.assertTrue(is_archived(self.root, 'ISOP-2027'))
        self.assertFalse(is_archived(self.root, 'ISOP-2100'))
        self.assertEqual(requirement_dir(self.root, 'ISOP-2200'), self.root / 'requirements/ISOP-2200')

    def test_duplicate_id_is_rejected(self):
        (self.root / 'requirements/ISOP-2027').mkdir()
        with self.assertRaises(ValueError): requirement_dir(self.root, 'ISOP-2027')
        with self.assertRaises(ValueError): requirement_dirs(self.root, include_history=True)

    def test_identifier_cannot_escape_requirements(self):
        with self.assertRaises(ValueError): requirement_dir(self.root, '../ISOP-2027')
