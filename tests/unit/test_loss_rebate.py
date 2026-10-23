import unittest
from contextlib import redirect_stdout
from decimal import Decimal
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from filbet.loss_rebate import (ROOT, ContractError, auth_denied, check_key, coverage_features, evidence_status, pages_equal,
                                parse_page, precision_result, public_observation, run_readonly, scoped_query, validate_stats_day)


class LossRebateChecks(unittest.TestCase):
    def test_real_report_shape_and_empty_response(self):
        response = {"http": 200, "body": {"status": True, "data": {"data": [{"id": "1"}], "t": 1, "s": {"num": 1}}}}
        self.assertEqual(parse_page(response)[0], [{"id": "1"}])
        response["body"]["data"] = {"d": [{"id": "1"}], "t": 1}
        with self.assertRaises(ContractError):
            parse_page(response)
        response["body"]["data"] = {"data": None, "t": 0, "s": None}
        self.assertEqual(parse_page(response)[0], [])

    def test_decimal_precision_does_not_invent_rounding(self):
        self.assertEqual(precision_result(Decimal("0.30"), Decimal("0.1") + Decimal("0.2")), "PASS")
        self.assertEqual(precision_result(Decimal("1.23"), Decimal("1.2345")), "NOT_RUN")
        self.assertEqual(precision_result(Decimal("150"), Decimal("401.75")), "FAIL")
        self.assertEqual(precision_result(Decimal("1.23"), Decimal("1.24")), "FAIL")

    def test_auth_error_with_leaked_rows_is_rejected(self):
        safe = {"http": 200, "body": {"status": False, "data": "token"}}
        self.assertTrue(auth_denied(safe))
        leaked = {"http": 401, "body": {"status": False, "data": {"data": [{"uid": "private"}]}}}
        self.assertFalse(auth_denied(leaked))

    def test_pagination_requires_unique_complete_set(self):
        rows = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        self.assertTrue(pages_equal([rows[:2], rows[2:]], rows))
        self.assertFalse(pages_equal([rows[:2]], rows))
        with self.assertRaises(ContractError):
            pages_equal([rows[:2], [{"id": "2"}]], rows)

    def test_public_observation_has_no_identity_or_response_text(self):
        response = {"http": 200, "body": {"status": True, "message": "private email", "data": {"data": [{"uid": "private", "phone": "123456789", "username": "private"}], "t": 1, "s": {"num": 1}}}}
        summary = public_observation(response)
        self.assertEqual(summary["row_count"], 1)
        self.assertNotIn("private", str(summary))
        self.assertNotIn("123456789", str(summary))

    def test_empty_baseline_cannot_verify_business_or_pagination(self):
        self.assertEqual(evidence_status([], [], []), "NOT_RUN")
        self.assertEqual(evidence_status([{"id": "1"}], [], []), "PASS")
        self.assertEqual(coverage_features([])["negative_rule_rows"], 0)
        self.assertEqual(check_key("冻结规则返利按max净输乘历史比例"), "rule-bonus")

    def test_coverage_exposes_missing_negative_and_unlimited_samples(self):
        rows = [{"conf": [{"net_loss_amount": "1"}, {"net_loss_amount": "2"}],
                 "upper_limit": "150", "lower_limit": "0", "net_loss_amount": "3"}]
        features = coverage_features(rows)
        self.assertEqual(features["multi_rule_rows"], 1)
        self.assertEqual(features["negative_rule_rows"], 0)
        self.assertEqual(features["zero_cap_rows"], 0)
        self.assertEqual(features["zero_gate_rows"], 1)

    def test_stats_day_rejects_invalid_dates_and_conflicting_queries(self):
        for invalid in ("20261012", "2026-02-30", "2026-10-12T00:00:00", "2026-1-2"):
            with self.assertRaises(ValueError):
                validate_stats_day(invalid)
        query = {"page": 1, "uid": "fixture"}
        self.assertEqual(scoped_query(query), query)
        self.assertEqual(scoped_query(query, "2026-10-12"), {**query, "stime": "2026-10-12", "etime": "2026-10-12"})
        self.assertNotIn("stime", query)
        with self.assertRaises(ValueError):
            scoped_query({"stime": "2026-10-09"}, "2026-10-12")

    def test_selected_day_rejects_mixed_rows_instead_of_hiding_old_failure(self):
        response = {"http": 200, "body": {"status": True, "data": {"data": [
            {"id": "old-failed-row", "stats_day": "2026-10-09"},
            {"id": "new-row", "stats_day": "20261012"}], "t": 2, "s": None}}}
        self.assertEqual(len(parse_page(response)[0]), 2)  # Existing unscoped contract stays compatible.
        with self.assertRaises(ContractError):
            parse_page(response, stats_day="2026-10-12")

    def test_scoped_empty_suite_stays_unverified_and_constrains_every_get(self):
        class EmptySession:
            def __init__(self):
                self.token, self.requests = "", []
            def login(self):
                self.token = "fixture-memory-only"
            def request(self, method, path, *, query, auth):
                self.requests.append((method, path, query, auth))
                if auth != "valid":
                    return {"http": 200, "body": {"status": False, "data": "token"}}
                return {"http": 200, "body": {"status": True, "data": {"data": None, "t": 0, "s": {"num": 0, "net_loss_amount": 0, "bonus": 0, "multiple_amount": 0}}}}
        session = EmptySession()
        config = {"ADMIN_URL": "https://admin-fat.filbet2025.com", "API_URL": "https://client-fat.filbet2025.com"}
        with TemporaryDirectory(dir=ROOT / "reports") as temporary:
            args = SimpleNamespace(env=".env.fat", stats_day="2026-10-12", execute=True, insecure=False, out=Path(temporary).relative_to(ROOT))
            with patch("filbet.loss_rebate.Session", return_value=session), patch("filbet.loss_rebate.load_environment", return_value=config), redirect_stdout(StringIO()):
                self.assertEqual(run_readonly(args), 0)
            report = json.loads(next(Path(temporary).glob("api-readonly-*/result.json")).read_text())
            business_keys = {"main-nl", "rule-nl", "nl-sum", "rule-bonus", "before-cap", "formula-before-cap", "actual-cap", "turnover", "threshold", "uid-day", "pagination", "summary"}
            self.assertTrue(all(row["status"] == "NOT_RUN" for row in report["results"] if row["check_key"] in business_keys))
            self.assertEqual(report["stats_day"], "2026-10-12")
            self.assertTrue(all(query["stime"] == query["etime"] == "2026-10-12" for _, _, query, _ in session.requests))
            self.assertEqual({auth for _, _, _, auth in session.requests}, {"valid", "missing", "invalid"})
            self.assertEqual(len([row for row in report["requests"] if row["label"].startswith("date-")]), 1)
            self.assertEqual(session.token, "")


if __name__ == "__main__":
    unittest.main()
