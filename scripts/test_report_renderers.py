import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
