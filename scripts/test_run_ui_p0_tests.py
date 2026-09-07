import argparse
import importlib.util
import tempfile
import unittest
from contextlib import chdir
from pathlib import Path
from unittest.mock import patch


def load_script(name: str):
    path = Path(__file__).with_name(name)
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


UI_RUNNER = load_script("run-ui-p0-tests.py")


class UiRunnerReportTests(unittest.TestCase):
    def test_fallback_report_records_success_or_failure(self):
        for status in ("PASS", "FAILED"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory, chdir(directory):
                UI_RUNNER.write_fallback_report({
                    "scope": "FAT", "status": status, "stage": "report",
                    "error": "main report generation failed",
                })
                html_report = Path("ui/reports/p0-ui-report.html").read_text(encoding="utf-8")
                markdown_report = Path("ui/reports/p0-ui-report.md").read_text(encoding="utf-8")

                self.assertIn("P0 UI BLOCKED", html_report)
                self.assertIn("环境：FAT", html_report)
                self.assertIn(f"UI 运行状态：**{status}**", markdown_report)

    def test_main_writes_fallback_when_renderer_fails_after_any_test_result(self):
        for test_code, expected_exit, test_status in ((0, 127, "PASS"), (1, 1, "FAILED")):
            with self.subTest(test_code=test_code), tempfile.TemporaryDirectory() as directory, chdir(directory):
                with patch.object(UI_RUNNER, "run", side_effect=[0, test_code, 127]), \
                        patch.object(UI_RUNNER, "load_env", return_value={}), \
                        patch.object(UI_RUNNER, "preflight"), \
                        patch("sys.argv", ["run-ui-p0-tests.py"]):
                    exit_code = UI_RUNNER.main()
                document = Path("ui/reports/p0-ui-report.html").read_text(encoding="utf-8")
                status = Path("ui/results/p0-ui-run-status.json").read_text(encoding="utf-8")

                self.assertEqual(exit_code, expected_exit)
                self.assertIn("P0 UI BLOCKED", document)
                self.assertIn(f'"status": "{"FAILED" if test_status == "PASS" else test_status}"', status)

    def test_preflight_rejects_cross_environment_client_url(self):
        args = argparse.Namespace(scope="FAT")
        env = {
            "CLIENT_BASE_URL": "https://client-uat.example.test",
            "CLIENT_PHONE": "placeholder",
            "CLIENT_PASSWORD": "placeholder",
            "PRE_KYC_CLIENT_PHONE": "placeholder",
            "PRE_KYC_CLIENT_PASSWORD": "placeholder",
            "CLIENT_AUTH_MODE": "password",
        }
        with self.assertRaisesRegex(SystemExit, "FAT scope cannot use a UAT CLIENT_BASE_URL"):
            UI_RUNNER.preflight(args, env)

    def test_preflight_rejects_fixed_otp_for_uat(self):
        args = argparse.Namespace(scope="UAT")
        env = {
            "CLIENT_BASE_URL": "https://client-uat.example.test",
            "CLIENT_PHONE": "placeholder",
            "CLIENT_OTP": "placeholder",
            "PRE_KYC_CLIENT_PHONE": "placeholder",
            "PRE_KYC_CLIENT_PASSWORD": "placeholder",
            "CLIENT_AUTH_MODE": "otp",
            "CLIENT_OTP_SOURCE": "fixed",
        }
        with self.assertRaisesRegex(SystemExit, "UAT UI requires CLIENT_AUTH_MODE=otp"):
            UI_RUNNER.preflight(args, env)

    def test_sanitize_error_redacts_sensitive_environment_values(self):
        message = UI_RUNNER.sanitize_error(
            "login failed for secret-phone?token=secret-token",
            {"CLIENT_PHONE": "secret-phone", "API_TOKEN": "secret-token"},
        )
        self.assertNotIn("secret-phone", message)
        self.assertNotIn("secret-token", message)

    def test_load_env_preserves_full_flow_shell_overrides(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env.fat"
            env_file.write_text("CLIENT_PHONE=file-account\nCLIENT_PASSWORD=file-password\n", encoding="utf-8")
            with patch.dict("os.environ", {
                "ENV_FILE_PRECEDENCE": "shell",
                "CLIENT_PHONE": "current-flow-account",
            }, clear=True):
                env = UI_RUNNER.load_env(env_file)

        self.assertEqual(env["CLIENT_PHONE"], "current-flow-account")
        self.assertEqual(env["CLIENT_PASSWORD"], "file-password")
        self.assertEqual(env["CLIENT_REUSE_P0_AUTH"], "true")

    def test_interrupt_still_writes_status_and_fallback_report(self):
        with tempfile.TemporaryDirectory() as directory, chdir(directory):
            with patch.object(UI_RUNNER, "run", side_effect=[KeyboardInterrupt(), 0]), patch(
                "sys.argv", ["run-ui-p0-tests.py"]
            ):
                exit_code = UI_RUNNER.main()
            status = Path("ui/results/p0-ui-run-status.json").read_text(encoding="utf-8")
            report = Path("ui/reports/p0-ui-report.html").read_text(encoding="utf-8")

        self.assertEqual(exit_code, 130)
        self.assertIn('"status": "INTERRUPTED"', status)
        self.assertIn("P0 UI BLOCKED", report)

    def test_unknown_environment_error_still_writes_failure_report(self):
        with tempfile.TemporaryDirectory() as directory, chdir(directory):
            with patch.object(UI_RUNNER, "run", side_effect=[0, 0]), \
                    patch.object(UI_RUNNER, "load_env", side_effect=RuntimeError("unexpected")), \
                    patch("sys.argv", ["run-ui-p0-tests.py"]):
                exit_code = UI_RUNNER.main()
            status = Path("ui/results/p0-ui-run-status.json").read_text(encoding="utf-8")
            report = Path("ui/reports/p0-ui-report.html").read_text(encoding="utf-8")

        self.assertEqual(exit_code, 1)
        self.assertIn('"stage": "environment"', status)
        self.assertIn("P0 UI BLOCKED", report)

    def test_report_interrupt_is_recorded_as_interrupted(self):
        with tempfile.TemporaryDirectory() as directory, chdir(directory):
            with patch.object(UI_RUNNER, "run", side_effect=[0, 0, KeyboardInterrupt()]), \
                    patch.object(UI_RUNNER, "load_env", return_value={}), \
                    patch.object(UI_RUNNER, "preflight"), \
                    patch("sys.argv", ["run-ui-p0-tests.py"]):
                exit_code = UI_RUNNER.main()
            status = Path("ui/results/p0-ui-run-status.json").read_text(encoding="utf-8")
            report = Path("ui/reports/p0-ui-report.html").read_text(encoding="utf-8")

        self.assertEqual(exit_code, 130)
        self.assertIn('"status": "INTERRUPTED"', status)
        self.assertIn('"stage": "report"', status)
        self.assertIn("P0 UI BLOCKED", report)

    def test_headed_flag_sets_visible_playwright_environment(self):
        playwright_env = {}

        def record_run(command, env):
            if command[:3] == ["npx", "playwright", "test"]:
                playwright_env.update(env)
            return 0

        with tempfile.TemporaryDirectory() as directory, chdir(directory):
            with patch.object(UI_RUNNER, "run", side_effect=record_run), \
                    patch.object(UI_RUNNER, "load_env", return_value={}), \
                    patch.object(UI_RUNNER, "preflight"), \
                    patch.object(UI_RUNNER.Path, "is_file", return_value=True), \
                    patch("sys.argv", ["run-ui-p0-tests.py", "--headed"]):
                self.assertEqual(UI_RUNNER.main(), 0)

        self.assertEqual(playwright_env["PLAYWRIGHT_HEADLESS"], "false")


if __name__ == "__main__":
    unittest.main()
