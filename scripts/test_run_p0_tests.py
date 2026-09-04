import argparse
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("run-p0-tests.py")
SPEC = importlib.util.spec_from_file_location("run_p0_tests", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)

API_MODULE_PATH = Path(__file__).with_name("run-api-tests.py")
API_SPEC = importlib.util.spec_from_file_location("run_api_tests", API_MODULE_PATH)
API_MODULE = importlib.util.module_from_spec(API_SPEC)
assert API_SPEC.loader
API_SPEC.loader.exec_module(API_MODULE)


class CommandRedactionTests(unittest.TestCase):
    def test_called_process_error_contains_only_redacted_command(self):
        command = ["tool", "--client-phone", "sensitive-phone", "--approval-code", "sensitive-code"]
        original = subprocess.CalledProcessError(7, command)
        with patch.object(MODULE.subprocess, "run", side_effect=original):
            with self.assertRaises(subprocess.CalledProcessError) as caught:
                MODULE.run(command, {})
        rendered = str(caught.exception)
        self.assertNotIn("sensitive-phone", rendered)
        self.assertNotIn("sensitive-code", rendered)
        self.assertEqual(rendered.count("<redacted>"), 2)

    def test_api_error_message_redacts_env_and_query_secrets(self):
        error = RuntimeError(
            "request failed password-value https://example.test/path?token=token-value&phone=9000000000"
        )
        rendered = API_MODULE.sanitize_error(
            error,
            {"ADMIN_PASSWORD": "password-value", "API_TOKEN": "token-value"},
        )
        self.assertNotIn("password-value", rendered)
        self.assertNotIn("token-value", rendered)
        self.assertNotIn("9000000000", rendered)
        self.assertGreaterEqual(rendered.count("<redacted>"), 3)


class FullOrchestrationTests(unittest.TestCase):
    def test_preflight_runs_first_and_kyc_precedes_deposit_suite(self):
        env = {
            "WRITE_CLIENT_PHONE": "9000000001",
            "WRITE_CLIENT_PASSWORD": "write-password",
            "KYC_CLIENT_PHONE": "9000000002",
            "KYC_CLIENT_PASSWORD": "kyc-password",
            "PRE_KYC_CLIENT_PHONE": "9000000003",
            "PRE_KYC_CLIENT_PASSWORD": "basic-password",
            "CLIENT_PASSWORD": "client-password",
            "CLIENT_AUTH_MODE": "password",
        }
        events = []

        def record_run(command, _env):
            events.append(command)

        with (
            patch.object(sys, "argv", ["run-p0-tests.py", "--mode", "full"]),
            patch.object(MODULE, "load_env", return_value=env),
            patch.object(MODULE, "preflight_full", side_effect=lambda *_: events.append("preflight")),
            patch.object(MODULE, "run", side_effect=record_run),
            patch.object(MODULE, "run_default_ui", side_effect=lambda *_args, **_kwargs: events.append("default-ui")),
        ):
            MODULE.main()

        self.assertEqual(events[0], "preflight")
        kyc_index = next(index for index, item in enumerate(events) if isinstance(item, list) and "--complete-kyc" in item)
        deposit_suite_index = next(index for index, item in enumerate(events) if isinstance(item, list) and "scripts/run-api-tests.py" in item)
        self.assertLess(kyc_index, deposit_suite_index)


class ApiReportTests(unittest.TestCase):
    def test_failed_p0_run_renders_main_report_once(self):
        failure = subprocess.CalledProcessError(2, "redacted")
        status = {"status": "FAILED", "stage": "safe_smoke", "exit_code": 2}
        with (
            patch.object(sys, "argv", ["run-api-tests.py", "p0", "--no-clean"]),
            patch.object(API_MODULE, "load_env", return_value={}),
            patch.object(API_MODULE, "preflight"),
            patch.object(API_MODULE, "run_p0", side_effect=failure),
            patch.object(API_MODULE, "write_run_status", return_value=status),
            patch.object(API_MODULE, "render_report_resilient", return_value=status) as render,
            patch("builtins.print") as output,
        ):
            self.assertEqual(API_MODULE.main(), 2)
        render.assert_called_once()
        self.assertTrue(
            any(
                str(call.args[0]).startswith("HTML report: file://")
                and str(call.args[0]).endswith("/api/results/p0-api-report.html")
                for call in output.call_args_list
            )
        )

    def test_preflight_failure_is_converted_to_reported_exit(self):
        status = {"status": "FAILED", "stage": "preflight", "exit_code": 1}
        with (
            patch.object(sys, "argv", ["run-api-tests.py", "p0", "--no-clean"]),
            patch.object(API_MODULE, "load_env", return_value={}),
            patch.object(API_MODULE, "preflight", side_effect=SystemExit("missing config")),
            patch.object(API_MODULE, "write_run_status", return_value=status) as write_status,
            patch.object(API_MODULE, "render_report_resilient", return_value=status) as render,
        ):
            self.assertEqual(API_MODULE.main(), 1)
        write_status.assert_called_once()
        render.assert_called_once()

    def test_unexpected_failure_is_converted_to_reported_exit(self):
        status = {"status": "FAILED", "stage": "safe_smoke", "exit_code": 1}
        with (
            patch.object(sys, "argv", ["run-api-tests.py", "p0", "--no-clean"]),
            patch.object(API_MODULE, "load_env", return_value={}),
            patch.object(API_MODULE, "preflight"),
            patch.object(API_MODULE, "run_p0", side_effect=RuntimeError("unexpected")),
            patch.object(API_MODULE, "write_run_status", return_value=status) as write_status,
            patch.object(API_MODULE, "render_report_resilient", return_value=status) as render,
        ):
            self.assertEqual(API_MODULE.main(), 1)
        self.assertIn("unexpected", write_status.call_args.kwargs["error"])
        render.assert_called_once()

    def test_report_renderer_failure_writes_fallback_without_raising(self):
        args = argparse.Namespace(scope="FAT", safe_only=False)
        status = {"status": "FAILED", "stage": "negative", "error": "case failed", "exit_code": 1}
        with (
            patch.object(API_MODULE, "render_p0_api_report", side_effect=RuntimeError("renderer failed")),
            patch.object(API_MODULE, "write_run_status", return_value=status) as write_status,
            patch.object(API_MODULE, "write_fallback_report") as fallback,
        ):
            returned = API_MODULE.render_report_resilient(args, {}, status, "start")
        write_status.assert_called_once()
        fallback.assert_called_once_with(args, status)
        self.assertIs(returned, status)

    def test_status_artifact_failure_still_attempts_fallback_report(self):
        args = argparse.Namespace(scope="FAT", safe_only=False)
        status = {"status": "FAILED", "stage": "negative", "error": "case failed", "exit_code": 1}
        with (
            patch.object(API_MODULE, "render_p0_api_report", side_effect=RuntimeError("renderer failed")),
            patch.object(API_MODULE, "write_run_status", side_effect=OSError("status unavailable")),
            patch.object(API_MODULE, "write_fallback_report") as fallback,
        ):
            returned = API_MODULE.render_report_resilient(args, {}, status, "start")
        fallback.assert_called_once_with(args, status)
        self.assertIn("status artifact failed", returned["report_error"])


class ApiEntrypointTests(unittest.TestCase):
    def test_full_api_controlled_flow_has_deterministic_business_order(self):
        args = argparse.Namespace(
            current_stage="",
            scope="FAT",
            safe_only=False,
            env=".env.fat",
            body_format="cbor",
            insecure=True,
            register_phone="",
            write_client_phone="",
            write_client_otp="",
            deposit_pid="",
            deposit_amount="1200",
            maya_pid="47870583692853381",
            kyc_image="21000000008072.webp",
            withdraw_amount="100",
        )
        commands = []
        with patch.object(API_MODULE, "run", side_effect=lambda command, _env: commands.append(command)):
            API_MODULE.run_p0(args, {})
        controlled = next(command for command in commands if "scripts/api-controlled-flow-runner.py" in command)
        ordered_flags = [
            "--register",
            "--complete-kyc",
            "--deposit",
            "--clear-turnover",
            "--prepare-withdraw-account",
            "--withdraw",
            "--check-client-withdraw-list",
            "--check-admin-withdraw-list",
            "--approve-withdraw",
        ]
        positions = [controlled.index(flag) for flag in ordered_flags]
        self.assertEqual(positions, sorted(positions))

    def test_scope_is_inferred_from_environment_filename(self):
        self.assertEqual(API_MODULE.infer_scope(".env.fat", ""), "FAT")
        self.assertEqual(API_MODULE.infer_scope(".env.uat", ""), "UAT")
        self.assertEqual(API_MODULE.infer_scope("custom.env", "uat"), "UAT")

    def test_preflight_fails_before_execution_when_credentials_are_missing(self):
        args = argparse.Namespace(scope="FAT", safe_only=True)
        with self.assertRaisesRegex(SystemExit, "P0 API preflight failed"):
            API_MODULE.preflight(args, {"API_URL": "https://client-fat.example.com"})


if __name__ == "__main__":
    unittest.main()
