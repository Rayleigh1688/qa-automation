import io
import importlib.util
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from filbet.loss_rebate import (ROOT, ContractError, auth_denied, check_key, coverage_features, evidence_status, pages_equal,
                                parse_page, precision_result, public_observation, run_readonly, scoped_query,
                                selected_dates, validate_stats_day)


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
            with patch("filbet.loss_rebate.Session", return_value=session), patch("filbet.loss_rebate.load_environment", return_value=config), redirect_stdout(io.StringIO()):
                self.assertEqual(run_readonly(args), 0)
            report = json.loads(next(Path(temporary).glob("api-readonly-*/result.json")).read_text())
            business_keys = {"main-nl", "rule-nl", "nl-sum", "rule-bonus", "before-cap", "formula-before-cap", "actual-cap", "turnover", "threshold", "uid-day", "pagination", "summary"}
            self.assertTrue(all(row["status"] == "NOT_RUN" for row in report["results"] if row["check_key"] in business_keys))
            self.assertEqual(report["stats_day"], "2026-10-12")
            self.assertTrue(all(query["stime"] == query["etime"] == "2026-10-12" for _, _, query, _ in session.requests))
            self.assertEqual({auth for _, _, _, auth in session.requests}, {"valid", "missing", "invalid"})
            self.assertEqual(len([row for row in report["requests"] if row["label"].startswith("date-")]), 1)
            self.assertEqual(session.token, "")

    def test_requested_window_is_inclusive_and_bounded(self):
        query, days = selected_dates(SimpleNamespace(start_date="2026-10-12", end_date="2026-10-15"))
        self.assertEqual(query, {"stime": "2026-10-12", "etime": "2026-10-15"})
        self.assertEqual(days, ["2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15"])
        self.assertEqual(selected_dates(SimpleNamespace())[0], {})
        self.assertEqual(selected_dates(SimpleNamespace(stats_day="2026-10-12")),
                         ({"stime": "2026-10-12", "etime": "2026-10-12"}, ["2026-10-12"]))
        for start, end in [("2026-10-12", None), (None, "2026-10-15"),
                           ("2026-10-15", "2026-10-12"), ("2026-02-30", "2026-03-01"),
                           ("2026-10-01", "2026-11-01"), ("20261012", "20261015")]:
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                selected_dates(SimpleNamespace(start_date=start, end_date=end))

    def test_day_and_window_are_rejected_before_loading_credentials_or_login(self):
        for window in ({"start_date": "2026-10-12"}, {"end_date": "2026-10-12"},
                       {"start_date": "2026-10-12", "end_date": "2026-10-12"}):
            args = SimpleNamespace(env=".env.fat", execute=True, stats_day="2026-10-12", **window)
            with self.subTest(window=window), patch("filbet.loss_rebate.load_environment") as load, \
                    patch("filbet.loss_rebate.Session") as session:
                with self.assertRaisesRegex(ValueError, "--stats-day cannot combine"):
                    run_readonly(args)
                load.assert_not_called()
                session.assert_not_called()

    def test_archived_cli_rejects_day_window_and_reassessment_combinations(self):
        path = ROOT / "requirements/history/archived-20261020/ISOP-2090/api/run-readonly.py"
        spec = importlib.util.spec_from_file_location("loss_rebate_readonly_combination_cli", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        combinations = [
            ["--stats-day", "2026-10-12", "--start-date", "2026-10-12"],
            ["--stats-day", "2026-10-12", "--end-date", "2026-10-12"],
            ["--reassess", "unused.json", "--stats-day", "2026-10-12"],
            ["--reassess", "unused.json", "--start-date", "2026-10-12", "--end-date", "2026-10-12"],
            ["--reassess", "unused.json", "--execute"],
        ]
        for options in combinations:
            with self.subTest(options=options), patch("sys.argv", [str(path), *options]), \
                    patch.object(module, "run_readonly") as collect, \
                    patch.object(module, "reassess_recorded") as reassess, \
                    redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                module.main()
            self.assertEqual(raised.exception.code, 2)
            collect.assert_not_called()
            reassess.assert_not_called()

    def test_bad_window_stops_before_loading_credentials_or_login(self):
        args = SimpleNamespace(env=".env.fat", execute=True, start_date="2026-10-12", end_date=None)
        with patch("filbet.loss_rebate.load_environment") as load, patch("filbet.loss_rebate.Session") as session:
            with self.assertRaises(ValueError):
                run_readonly(args)
        load.assert_not_called()
        session.assert_not_called()

    def test_collection_applies_window_to_all_filters_and_final_reference(self):
        calls = []
        records = []
        for ident, day in enumerate(("2026-10-01", "2026-10-12", "2026-10-15"), 1):
            records.append({"id": str(ident), "uid": "fixture-member", "username": "fixture-user",
                            "phone": "fixture-phone", "vip": "1", "level": "bronze", "stats_day": day,
                            "valid_bet_amount": "500", "payout_amount": "0", "net_loss_amount": "500",
                            "capped_amount": "5", "bonus": "5", "lower_limit": "100", "upper_limit": "150",
                            "multiple": "2", "multiple_amount": "10",
                            "conf": [{"valid_bet_amount": "500", "payout_amount": "0", "net_loss_amount": "500",
                                      "rate": "1", "bonus": "5"}]})

        class FakeSession:
            def __init__(self, *args, **kwargs): self.token = ""
            def login(self): pass
            def request(self, method, path, *, query, auth="valid"):
                calls.append((dict(query), auth))
                if auth != "valid":
                    return {"http": 401, "body": {"status": False, "data": None}}
                selected = [row for row in records if query.get("stime", "") <= row["stats_day"] <= query.get("etime", "9999")]
                for key in ("uid", "username", "phone", "vip", "level"):
                    if key in query:
                        selected = [row for row in selected if row[key] == query[key]]
                page, size = query["page"], query["page_size"]
                summary = {"num": len({r['uid'] for r in selected}),
                           **{key: str(sum(Decimal(r[key]) for r in selected))
                              for key in ("net_loss_amount", "bonus", "multiple_amount")}}
                return {"http": 200, "body": {"status": True, "data": {
                    "data": selected[(page - 1) * size:page * size], "t": len(selected), "s": summary}}}

        scopes = [
            ({"start_date": "2026-10-12", "end_date": "2026-10-15"},
             ["2026-10-12", "2026-10-15"], ["2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15"]),
            ({"stats_day": "2026-10-12"}, ["2026-10-12"], ["2026-10-12"]),
        ]
        for scope, expected_dates, filter_days in scopes:
            calls.clear()
            with self.subTest(scope=scope), TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                args = SimpleNamespace(env=".env.fat", execute=True, insecure=False, out=root / "reports", **scope)
                config = {"ADMIN_URL": "https://admin-fat.filbet2025.com", "API_URL": "https://client-fat.filbet2025.com"}
                with patch("filbet.loss_rebate.ROOT", root), patch("filbet.loss_rebate.Session", FakeSession), \
                     patch("filbet.loss_rebate.load_environment", return_value=config), \
                     patch("filbet.loss_rebate.write_views"), redirect_stdout(io.StringIO()):
                    self.assertEqual(run_readonly(args), 0)
                report = json.loads(next(args.out.glob("api-readonly-*/result.json")).read_text())
                self.assertEqual(report["baseline"]["dates"], expected_dates)
                self.assertEqual(report["baseline"]["rows"], len(expected_dates))
                self.assertEqual(report["date_filter_days"], filter_days)
                if "stats_day" in scope:
                    self.assertEqual(report["stats_day"], scope["stats_day"])
                self.assertTrue(all(row["status"] == "PASS" for row in report["results"]))
            for query, _ in calls:
                self.assertGreaterEqual(query["stime"], filter_days[0])
                self.assertLessEqual(query["etime"], filter_days[-1])
            self.assertEqual(calls[0][0], calls[-1][0])
            self.assertTrue(any(query["page_size"] == 10 and auth == "valid" for query, auth in calls))
            self.assertEqual({key for query, _ in calls for key in ("uid", "username", "phone", "vip", "level") if key in query},
                             {"uid", "username", "phone", "vip", "level"})
            self.assertEqual({auth for _, auth in calls}, {"valid", "missing", "invalid"})


if __name__ == "__main__":
    unittest.main()
