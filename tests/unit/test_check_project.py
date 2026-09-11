from support import ROOT, SCRIPTS
import importlib.util
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("check_project", (SCRIPTS / "check-project.py"))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class NavigationCheckTests(unittest.TestCase):
    def test_detects_broken_links_and_commands_with_line_numbers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            doc = root / "README.md"
            doc.write_text("[missing](missing.md)\nnpm run typo\n")
            errors = MODULE.document_errors(doc, root, {"check"})
            self.assertEqual(len(errors), 2)
            self.assertIn("README.md:1", errors[0])
            self.assertIn("unknown npm command typo", errors[1])

    def test_latest_run_artifacts_may_be_absent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            doc = root / "README.md"
            doc.write_text("[report](api/results/report.html) [source](scripts/missing.py)")
            errors = MODULE.document_errors(doc, root, set())
            self.assertEqual(len(errors), 1)
            self.assertIn("scripts/missing.py", errors[0])

    def test_requirement_and_telegram_evidence_are_optional_but_sources_are_not(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            doc = root / 'README.md'
            doc.write_text('[run](reports/telegram/runs/example/report.md)\n'
                           '[team](reports/qa/ISOP-2027/team/manual.csv)\n'
                           '[current](reports/qa/ISOP-2027/latest.html)\n'
                           '[api](requirements/ISOP-2027/api/results/example/report.md)\n'
                           '[cases](requirements/ISOP-2027/api/cases.json)\n'
                           '[other](requirements/ISOP-2027/results/missing.md)\n')
            errors = MODULE.document_errors(doc, root, set())
            self.assertEqual(len(errors), 2)
            self.assertTrue(any('cases.json' in error for error in errors))
            self.assertTrue(any('ISOP-2027/results/missing.md' in error for error in errors))

    def test_accepts_relative_unicode_links_and_external_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "说明.md").write_text("# 标题")
            doc = root / "README.md"
            doc.write_text("[local](说明.md#标题) [web](https://example.com)\nnpm run check\n")
            self.assertEqual(MODULE.document_errors(doc, root, {"check"}), [])


if __name__ == "__main__":
    unittest.main()
