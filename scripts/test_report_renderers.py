import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from p0_report_template import format_east8_time, format_execution_duration, write_html_report


def load_script(name: str):
    path = Path(__file__).with_name(name)
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


API_REPORT = load_script("render-api-p0-report.py")
UI_REPORT = load_script("render-ui-p0-report.py")
MAIN_REPORT = load_script("render-main-flow-report.py")


class ApiReportTests(unittest.TestCase):
    def test_controlled_argument_accepts_multiple_stage_files(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.json"
            second = Path(directory) / "second.json"
            first.write_text(json.dumps([{"name": "register"}]), encoding="utf-8")
            second.write_text(json.dumps([{"name": "withdraw_create"}]), encoding="utf-8")
            records = API_REPORT.load_controlled([str(first), str(second)])
        self.assertEqual([item["name"] for item in records], ["register", "withdraw_create"])

    def test_combines_setup_positive_negative_and_controlled_results(self):
        cases = {
            "TC-001": {"flow_stage_label": "登录", "case_name": "会员详情", "assertions": "status_true"},
            "NTC-001": {"flow_stage_label": "登录", "case_name": "错误 OTP", "assertions": "business_not_true"},
        }
        positive = [
            {"method": "POST", "url": "https://example.test/login", "status": 200, "ok": True, "decoded_body": {"status": True, "data": "secret-token"}},
            {"case_id": "TC-001", "method": "GET", "url": "https://example.test/member/detail?phone=secret-phone", "status": 200, "assertion_passed": True, "decoded_body": {"status": True}},
        ]
        negative = [{"case_id": "NTC-001", "method": "POST", "url": "https://example.test/otp", "http_status": 200, "business_status": False, "assertion_passed": True}]
        controlled = [{"name": "deposit_create", "url": "https://example.test/deposit?id=secret-id", "http_status": 200, "business_status": True}]
        items = API_REPORT.build_items(cases, positive, negative, controlled)
        self.assertEqual(len(items), 4)
        self.assertTrue(all(item["status"] == "PASS" for item in items))
        rendered = str(items)
        self.assertNotIn("secret-token", rendered)
        self.assertNotIn("secret-phone", rendered)
        self.assertNotIn("secret-id", rendered)

    def test_synthetic_success_passes_and_obsolete_deposit_lookup_is_skipped(self):
        controlled = [
            {"name": "register_phone_allocate", "business_status": True},
            {
                "name": "admin_deposit_list",
                "http_status": 200,
                "business_status": False,
                "reason": "deposit order not found: id=1",
                "body_sample": '{"status": true, "data": {"d": null}}',
            },
        ]
        items = API_REPORT.build_items({}, [], [], controlled)
        self.assertEqual([item["status"] for item in items], ["PASS", "SKIPPED"])

    def test_async_verified_withdraw_makes_false_sync_response_non_gating(self):
        controlled = [
            {
                "name": "withdraw_create",
                "http_status": 200,
                "business_status": False,
                "body_sample": '{"status": false, "data": "late"}',
            },
            {
                "name": "client_withdraw_list",
                "http_status": 200,
                "business_status": True,
                "matched_order": {"id": "1", "status": "paying"},
            },
        ]
        items = API_REPORT.build_items({}, [], [], controlled)
        self.assertEqual([item["status"] for item in items], ["SKIPPED", "PASS"])

    def test_admin_withdraw_list_satisfies_planned_exact_query(self):
        controlled = [{
            "name": "admin_withdraw_list",
            "url": "https://admin.example.test/admin/finance/withdraw/list",
            "http_status": 200,
            "business_status": True,
            "matched_order": {"id": "1", "status": "paying"},
        }]
        items = API_REPORT.build_items({}, [], [], controlled)
        API_REPORT.add_planned_not_run(items, {}, include_controlled=True)
        exact_query_items = [item for item in items if item["name"] == "后台精确查询提现订单"]
        self.assertEqual(len(exact_query_items), 1)
        self.assertEqual(exact_query_items[0]["status"], "PASS")
        self.assertEqual(exact_query_items[0]["target"], "POST /admin/finance/withdraw/list")

    def test_missing_planned_cases_are_reported_as_not_run(self):
        cases = {
            "TC-001": {"execution_policy": "safe_smoke", "flow_stage_label": "登录", "case_name": "会员详情", "method": "GET", "path": "/member/detail", "assertions": "status_true"},
            "NTC-001": {"execution_policy": "negative_smoke", "flow_stage_label": "登录", "case_name": "错误 OTP", "method": "DYNAMIC", "path": "", "assertions": "business_not_true"},
        }
        items = []
        API_REPORT.add_planned_not_run(items, cases, include_controlled=True)
        self.assertEqual(
            sum(item["status"] == "NOT_RUN" for item in items),
            len(API_REPORT.PLANNED_LOGINS) + len(cases) + len(API_REPORT.PLANNED_CONTROLLED),
        )
        self.assertIn("TC-001", {item["id"] for item in items})
        self.assertIn("PLANNED-08", {item["id"] for item in items})


class UiReportTests(unittest.TestCase):
    def test_collects_playwright_pass_and_failure(self):
        source = {"suites": [{"specs": [{
            "title": "login scenarios", "file": "ui/cases/client-login.spec.mjs", "tests": [
                {"title": "login succeeds", "ok": True, "results": [{"status": "passed", "duration": 10}]},
                {"title": "bad login rejected", "ok": False, "results": [{"status": "failed", "duration": 20, "error": {"message": "expected rejection"}}]},
            ],
        }]}]}
        items = UI_REPORT.collect_tests(source)
        self.assertEqual([item["status"] for item in items], ["PASS", "FAIL"])
        self.assertEqual([item["id"] for item in items], ["UI-001", "UI-002"])

    def test_forced_failed_run_is_blocked_without_collected_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            html_output = Path(directory) / "report.html"
            markdown_output = Path(directory) / "report.md"
            with patch("sys.argv", [
                "render-ui-p0-report.py",
                "--input", str(Path(directory) / "missing.json"),
                "--run-status", "FAILED",
                "--out", str(markdown_output),
                "--html-out", str(html_output),
            ]):
                UI_REPORT.main()
            document = html_output.read_text(encoding="utf-8")

        self.assertIn("BLOCKED", document)

    def test_forced_successful_run_with_passed_test_is_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "result.json"
            source.write_text(json.dumps({"suites": [{"specs": [{
                "title": "login", "file": "ui/cases/client-login.spec.mjs",
                "tests": [{"title": "login succeeds", "ok": True, "results": [{"status": "passed"}]}],
            }]}]}), encoding="utf-8")
            expected = Path(directory) / "expected.json"
            expected.write_text(json.dumps([{
                "id": "UI-001", "file": "client-login.spec.mjs", "title": "login succeeds",
            }]), encoding="utf-8")
            html_output = Path(directory) / "report.html"
            with patch("sys.argv", [
                "render-ui-p0-report.py", "--input", str(source), "--run-status", "PASS",
                "--expected", str(expected),
                "--out", str(Path(directory) / "report.md"), "--html-out", str(html_output),
            ]):
                UI_REPORT.main()
            document = html_output.read_text(encoding="utf-8")

        self.assertIn("<strong>PASS</strong>", document)

    def test_missing_expected_test_is_not_run(self):
        items = UI_REPORT.apply_expected_tests([], [{
            "id": "UI-001", "file": "client-login.spec.mjs", "title": "login",
            "displayName": "登录成功", "group": "登录",
        }])
        self.assertEqual(items[0]["status"], "NOT_RUN")
        self.assertEqual(items[0]["id"], "UI-001")
        self.assertEqual(items[0]["name"], "登录成功")
        self.assertEqual(items[0]["group"], "登录")

    def test_expected_test_uses_chinese_report_labels_after_matching(self):
        items = UI_REPORT.apply_expected_tests([{
            "group": "client-login", "id": "UI-001", "name": "login succeeds", "kind": "UI",
            "status": "PASS", "target": "ui/cases/client-login.spec.mjs", "expected": "passed",
            "actual": "passed", "duration": "1ms", "detail": "",
        }], [{
            "id": "UI-001", "file": "client-login.spec.mjs", "title": "login succeeds",
            "displayName": "登录成功", "group": "登录",
        }])
        self.assertEqual(items[0]["name"], "登录成功")
        self.assertEqual(items[0]["group"], "登录")

    def test_unplanned_test_fails_fixed_suite_gate(self):
        items = UI_REPORT.apply_expected_tests([{
            "group": "extra", "id": "UI-001", "name": "unexpected", "kind": "UI",
            "status": "PASS", "target": "extra.spec.mjs", "expected": "", "actual": "passed",
            "duration": "1ms", "detail": "",
        }], [])
        self.assertEqual(items[0]["status"], "FAIL")
        self.assertEqual(items[0]["id"], "UI-UNPLANNED-001")


class MainFlowReportTests(unittest.TestCase):
    def setUp(self):
        self.controlled = [{
            "name": "p0_reconciliation",
            "business_status": True,
            "data": {
                "context": {
                    "deposit_amount": "1200",
                    "deposit_id": "deposit-1",
                    "bet_unit": 100,
                    "planned_spins": 10,
                    "completed_spins": 10,
                    "turnover_before_bet": "1800.00",
                    "turnover_after_bet": "800.00",
                    "turnover_final": "0",
                    "withdraw_amount": "1000",
                    "withdraw_id": "withdraw-1",
                    "withdraw_status": "under_review",
                },
                "checks": [{"passed": True} for _ in range(10)],
            },
        }]

    def test_real_bet_flow_displays_playwright_spin_evidence(self):
        status, detail = MAIN_REPORT.aggregate_flow_status(
            "MF-004", [], {}, {}, self.controlled
        )
        self.assertEqual(status, "通过")
        self.assertEqual(detail, "Playwright 真实投注 10/10 次；单注 100")

    def test_turnover_flow_displays_bet_progress_and_admin_clear(self):
        status, detail = MAIN_REPORT.aggregate_flow_status(
            "MF-005", [], {}, {}, self.controlled
        )
        self.assertEqual(status, "通过")
        self.assertEqual(detail, "投注流水 1800.00 → 800.00；管理后台清流后 0")

    def test_withdraw_flow_displays_same_order_evidence(self):
        status, detail = MAIN_REPORT.aggregate_flow_status(
            "MF-007", [], {}, {}, self.controlled
        )
        self.assertEqual(status, "通过")
        self.assertEqual(detail, "提现 1000；订单 withdraw-1；后台同单状态 under_review")


class SharedTemplateTests(unittest.TestCase):
    def test_formats_report_time_in_explicit_east_8_timezone(self):
        self.assertEqual(
            format_east8_time("2026-09-04T08:01:45+00:00"),
            "2026-09-04 16:01:45（UTC+8）",
        )

    def test_formats_execution_duration_from_run_status_timestamps(self):
        self.assertEqual(
            format_execution_duration(
                "2026-09-04T15:49:09.439419+08:00",
                "2026-09-04T15:50:12.541156+08:00",
            ),
            "1分03秒",
        )

    def test_shared_template_renders_summary_and_details(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.html"
            write_html_report(
                title="Example report", scope="FAT", report_kind="API", verdict="PASS",
                verdict_detail="all good", output=output,
                items=[{"group": "Auth", "id": "T-1", "name": "Login", "kind": "API", "status": "PASS", "target": "POST /login", "expected": "200", "actual": "200", "duration": "1ms", "detail": ""}],
            )
            document = output.read_text(encoding="utf-8")
        self.assertIn("Example report", document)
        self.assertIn("执行总数", document)
        self.assertIn("POST /login", document)

    def test_shared_template_renders_structured_business_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.html"
            write_html_report(
                title="Flow report", scope="FAT", report_kind="API + UI", verdict="PASS",
                verdict_detail="all good", output=output, items=[],
                evidence={
                    "highlights": [{"label": "真实投注", "value": "10/10 次", "detail": "单注 100"}],
                    "timeline": [{"step": "1", "title": "投注", "status": "PASS", "detail": "流水下降", "source": "Playwright"}],
                    "checks": [{"status": "PASS", "name": "投注完成", "detail": "planned=10, completed=10"}],
                    "images": [{"title": "投注后", "src": "after.png", "caption": "Spin 后状态"}],
                    "artifacts": [{"label": "核对 JSON", "href": "reconcile.json", "detail": "原始证据"}],
                },
            )
            document = output.read_text(encoding="utf-8")
        self.assertIn("本次执行摘要", document)
        self.assertIn("关键执行轨迹", document)
        self.assertIn("统一资金链核对", document)
        self.assertIn("Playwright 页面证据", document)
        self.assertIn('href="reconcile.json"', document)


if __name__ == "__main__":
    unittest.main()
