"""2090 CLI output paths are validated before login or artifact writes."""
import argparse
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from qa_core.output_paths import repository_output_path
from requirement_paths import requirement_dir


ROOT = Path(__file__).resolve().parents[2]
CLI_ROOT = requirement_dir(ROOT, "ISOP-2090") / "api"
CLI_NAMES = ("initial-read", "run-readonly", "run-client-readonly", "run-config", "static-sources")


def load_cli(name):
    spec = importlib.util.spec_from_file_location("loss_rebate_cli_" + name.replace("-", "_"), CLI_ROOT / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def arguments(name):
    return [name] + (["--admin-snapshot", "unused-dryrun-snapshot.json"] if name == "run-client-readonly" else [])


class LossRebateCliOutputPaths(unittest.TestCase):
    def test_all_clis_normalize_relative_and_default_paths_during_dryrun(self):
        for name in CLI_NAMES:
            module = load_cli(name)
            default = ROOT / "reports/qa/ISOP-2090/20261012-full"
            if name == "initial-read":
                default /= "evidence"
            elif name == "static-sources":
                default /= "evidence/source"
            for selected, expected in ((None, default), ("reports/qa/ISOP-2090/path-dryrun", ROOT / "reports/qa/ISOP-2090/path-dryrun")):
                with self.subTest(cli=name, selected=selected):
                    resolved = []
                    def normalize(value, root):
                        result = repository_output_path(value, root)
                        resolved.append(result)
                        return result
                    argv = arguments(name) + (["--out", selected] if selected else [])
                    with patch.object(module, "repository_output_path", side_effect=normalize), \
                            patch("sys.argv", argv), redirect_stdout(io.StringIO()):
                        self.assertEqual(module.main(), 0)
                    self.assertEqual(resolved, [expected.resolve()])
                    self.assertTrue(resolved[0].is_absolute())

    def test_all_clis_reject_outside_repository_before_execute(self):
        for name in CLI_NAMES:
            with self.subTest(cli=name):
                module = load_cli(name)
                argv = arguments(name) + ["--execute", "--out", str(ROOT.parent / "outside-2090-output")]
                with patch("sys.argv", argv), redirect_stderr(io.StringIO()) as output, \
                        self.assertRaises(SystemExit) as raised:
                    module.main()
                self.assertEqual(raised.exception.code, 2)
                self.assertIn("--out must resolve inside the repository", output.getvalue())

    def test_output_symlink_cannot_escape_repository(self):
        with tempfile.TemporaryDirectory(prefix=".unit-loss-rebate-", dir=ROOT) as inside, tempfile.TemporaryDirectory() as outside:
            link = Path(inside) / "external"
            link.symlink_to(Path(outside), target_is_directory=True)
            with self.assertRaises(argparse.ArgumentTypeError):
                repository_output_path(link / "new-output", ROOT)

    def test_relative_initial_collection_finishes_both_mock_reads_and_keeps_private_evidence(self):
        module = load_cli("initial-read")
        config = {"ADMIN_URL": "https://admin-fat.filbet2025.com", "API_URL": "https://client-fat.filbet2025.com"}
        response = {"http": 200, "body": {"status": True, "data": {"d": [], "t": 0}}}
        with tempfile.TemporaryDirectory(prefix=".unit-loss-rebate-", dir=ROOT) as temporary:
            folder = Path(temporary)
            argv = ["initial-read", "--execute", "--out", str(folder.relative_to(ROOT))]
            with patch("sys.argv", argv), patch.object(module, "load_environment", return_value=config), \
                    patch.object(module, "Session") as factory, redirect_stdout(io.StringIO()):
                session = factory.return_value
                session.request.return_value = response
                self.assertEqual(module.main(), 0)
            session.login.assert_called_once_with()
            self.assertEqual(session.request.call_count, 2)
            summary = json.loads(next(folder.glob("*-summary.json")).read_text())
            self.assertNotIn("error", summary)
            self.assertEqual(len(summary["probes"]), 2)
            for probe in summary["probes"]:
                evidence = ROOT / probe["private_evidence"]
                self.assertEqual(evidence.parent, folder)
                self.assertTrue(evidence.is_file())
                self.assertEqual(stat.S_IMODE(evidence.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
