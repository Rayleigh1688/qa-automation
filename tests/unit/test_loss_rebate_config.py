import json
import stat
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from filbet.loss_rebate_config import (
    ROOT, ContractError, GuardedChecks, NEGATIVE_KEYS, business, candidate_state, differences, finish, negative_body, private_json, save_body,
)


def baseline():
    return {"id": "41", "ty": 41, "name": "Test", "state": 1, "summary": "<p>original</p>", "multiple": "2",
            "recommend": 0, "daily_budget": "0", "send_amount": "0", "display_start_at": 1767596400000,
            "display_end_at": 1805492048000, "updated_at": 1, "updated_uid": "private", "updated_name": "private",
            "config": json.dumps({"venue": [{"name": "Slot", "game_class": "3", "rebate_ratio":
                                               [{"level": level, "ratio": "2"} for level in ("bronze", "silver", "gold", "platinum", "diamond")]}],
                                  "games": [{"name": "first", "list": ["111"], "rate": "3", "state": 0},
                                            {"name": "second", "list": ["222"], "rate": "4", "state": 1}],
                                  "exclude_games": ["333"], "turnover_limit": {"test": ["1"]}, "lower_limit": "100",
                                  "upper_limit": "150", "activity_range": 0, "user_list": [], "source_rule": 1,
                                  "popup_text": "Original", "order_review": 1, "received_type": 2})}


class FakeSession:
    def __init__(self, *, accept_duplicate=False, drift=False, timeout=False):
        self.row = baseline()
        self.original = deepcopy(self.row)
        self.posted = []
        self.gets = 0
        self.accept_duplicate, self.drift, self.timeout = accept_duplicate, drift, timeout

    def request(self, method, path, **kwargs):
        if method == "GET":
            self.gets += 1
            if self.drift and self.gets == 2:
                self.row["summary"] = "external"
            return {"http": 200, "body": {"status": True, "data": {"d": [deepcopy(self.row)], "t": 1}}}
        body = deepcopy(kwargs["body"])
        self.posted.append(body)
        if self.timeout:
            raise TimeoutError("sensitive response deliberately not recorded")
        conf = json.loads(body["config"])
        valid = body["summary"] != self.original["summary"] or conf == business(self.original)["config"] and body["multiple"] == "2"
        accepted = valid or self.accept_duplicate and len(self.posted) == 2
        if accepted:
            for key in ("name", "state", "summary", "multiple", "config"):
                self.row[key] = body[key]
            self.row["updated_at"] += 1
        return {"http": 200, "body": {"status": accepted, "data": None}}


class FakeClient:
    def __init__(self, admin):
        self.admin, self.token = admin, ""
        self.logins = 0

    def login_client_password(self):
        self.logins += 1
        self.token = "in-memory-test"

    def request(self, method, path, **kwargs):
        return {"http": 200, "body": {"status": True, "data": {"detail": self.admin.row["summary"]}}}


class ConfigurationContract(unittest.TestCase):
    def test_exact_registered_body_and_semantic_preservation(self):
        row = baseline()
        body = save_body(row)
        self.assertEqual(set(body), {"activity_type", "id", "name", "state", "start_at", "end_at",
                                     "source_introduction", "ty", "multiple", "config", "summary"})
        self.assertEqual(body["start_at"], "2026-01-05 15:00:00")
        self.assertEqual(body["end_at"], "2027-03-20 05:34:08")
        self.assertEqual(json.loads(body["config"]), business(row)["config"])
        changed = deepcopy(row)
        conf = json.loads(changed["config"])
        conf["games"][0]["name"] = " first "
        changed["config"] = json.dumps(conf)
        with self.assertRaises(ContractError):
            save_body(changed)
        conf["games"][0]["name"] = "😀" * 11
        changed["config"] = json.dumps(conf)
        with self.assertRaises(ContractError):
            save_body(changed)
        conf["games"][0]["name"] = "first"
        conf["venue"][0]["rebate_ratio"] = conf["venue"][0]["rebate_ratio"][:1]
        changed["config"] = json.dumps(conf)
        with self.assertRaises(ContractError):
            save_body(changed)

    def test_each_negative_is_independent_and_long_name_not_normalized(self):
        body = save_body(baseline())
        original = deepcopy(body)
        for key in NEGATIVE_KEYS:
            candidate = negative_body(body, key)
            self.assertNotEqual(candidate, body)
            self.assertEqual(body, original)
            conf = json.loads(candidate["config"])
            old = json.loads(body["config"])
            delta = {name for name in conf if conf[name] != old[name]}
            self.assertEqual(len(delta), 0 if key == "negative-multiple" else 1)
        self.assertEqual(len(json.loads(negative_body(body, "long-group-name")["config"])["games"][0]["name"]), 21)

    def execute(self, fake, marker=False):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "reports")
        self.addCleanup(temporary.cleanup)
        folder = Path(temporary.name)
        report = {"requests": [], "results": [], "run_id": "unit"}
        checks = GuardedChecks(fake, lambda: 123456, folder, report)
        client = FakeClient(fake) if marker else None
        checks.run(marker, client)
        return report, folder, client

    def test_first_unexpected_accept_stops_and_restores_without_hiding_failure(self):
        fake = FakeSession(accept_duplicate=True)
        report, _, _ = self.execute(fake)
        outcomes = {row["check_key"]: row["status"] for row in report["results"]}
        self.assertEqual(outcomes["same-value"], "PASS")
        self.assertEqual(outcomes["duplicate-game"], "FAIL")
        self.assertTrue(all(outcomes[key] == "NOT_RUN" for key in NEGATIVE_KEYS[1:]))
        self.assertEqual(len(fake.posted), 3)  # same value, invalid duplicate, independent cleanup
        self.assertEqual(report["restoration"]["status"], "RESTORED")
        self.assertFalse(differences(fake.original, fake.row))

    def test_external_cas_change_never_posts_or_restores(self):
        fake = FakeSession(drift=True)
        report, _, _ = self.execute(fake)
        self.assertEqual(fake.posted, [])
        self.assertEqual(fake.row["summary"], "external")
        self.assertNotIn("restoration", report)

    def test_ambiguous_post_is_not_retried_and_sensitive_exception_is_not_saved(self):
        fake = FakeSession(timeout=True)
        report, folder, _ = self.execute(fake)
        self.assertEqual(len(fake.posted), 1)
        self.assertEqual(report["results"][0]["status"], "FAIL")
        self.assertEqual(report["restoration"]["status"], "UNCHANGED")
        for path in folder.glob("*.json"):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            text = path.read_text()
            self.assertNotIn("sensitive response", text)
            self.assertNotIn('"google_code"', text)

    def test_marker_uses_one_client_session_and_restores_all_business_fields(self):
        fake = FakeSession()
        report, _, client = self.execute(fake, marker=True)
        self.assertEqual(client.logins, 1)
        self.assertEqual(client.token, "")
        self.assertEqual(report["results"][-1]["status"], "PASS")
        self.assertEqual(len(fake.posted), 12)  # same value, nine negatives, marker, restore
        self.assertEqual(business(fake.row), business(fake.original))

    def test_private_creation_does_not_overwrite_existing_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "evidence.json"
            private_json(path, {"first": True})
            with self.assertRaises(FileExistsError):
                private_json(path, {"second": True})
            self.assertEqual(json.loads(path.read_text()), {"first": True})

    def test_restore_never_adopts_extra_external_fields_after_own_post(self):
        fake = FakeSession()
        with tempfile.TemporaryDirectory(dir=ROOT / "reports") as temporary:
            report = {"requests": [], "results": [], "run_id": "unit"}
            checks = GuardedChecks(fake, lambda: 123456, Path(temporary), report)
            checks.baseline = baseline()
            candidate = negative_body(save_body(checks.baseline), "duplicate-group-name")
            observed = candidate_state(checks.baseline, candidate)
            observed["summary"] = "external after our write"
            self.assertFalse(checks.restore(observed, candidate))
            self.assertEqual(report["restoration"]["status"], "EXTERNAL_OR_UNKNOWN")
            self.assertEqual(fake.posted, [])

    def test_marker_only_has_no_negative_or_same_value_post(self):
        fake = FakeSession()
        with tempfile.TemporaryDirectory(dir=ROOT / "reports") as temporary:
            report = {"requests": [], "results": [], "run_id": "unit"}
            checks = GuardedChecks(fake, lambda: 123456, Path(temporary), report)
            client = FakeClient(fake)
            checks.run(client=client, marker_only=True)
            self.assertEqual(len(fake.posted), 2)
            self.assertEqual([item["check_key"] for item in report["results"]], ["rich-text-marker"])
            self.assertEqual(report["results"][0]["status"], "PASS")
            self.assertEqual(business(fake.row), business(fake.original))

    def test_restore_timeout_allows_no_second_restore_post(self):
        fake = FakeSession(timeout=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "reports") as temporary:
            report = {"requests": [], "results": [], "run_id": "unit"}
            checks = GuardedChecks(fake, lambda: 123456, Path(temporary), report)
            checks.baseline = baseline()
            candidate = negative_body(save_body(checks.baseline), "duplicate-group-name")
            fake.row = candidate_state(checks.baseline, candidate)
            self.assertFalse(checks.restore(fake.row, candidate))
            self.assertFalse(checks.restore(fake.row, candidate))
            self.assertEqual(len(fake.posted), 1)
            self.assertTrue(report["restoration"]["no_second_restore_post"])

    def test_interrupt_during_cleanup_preserves_one_failure_and_renders_unknown_restore(self):
        for marker_only in (False, True):
            with self.subTest(marker_only=marker_only), tempfile.TemporaryDirectory(dir=ROOT / "reports") as temporary:
                fake = FakeSession(accept_duplicate=not marker_only)
                report = {"requests": [], "results": [], "run_id": "unit"}
                calls = 0
                def code():
                    nonlocal calls
                    calls += 1
                    if calls == (2 if marker_only else 3):
                        raise KeyboardInterrupt()
                    return 123456
                checks = GuardedChecks(fake, code, Path(temporary), report)
                client = FakeClient(fake) if marker_only else None
                checks.run(client=client, marker_only=marker_only)
                failed = "rich-text-marker" if marker_only else "duplicate-game"
                results = [row for row in report["results"] if row["check_key"] == failed]
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0]["status"], "FAIL")
                self.assertEqual(report["restoration"]["status"], "UNKNOWN")
                self.assertIn("interrupted", report)
                self.assertEqual(len(fake.posted), 1 if marker_only else 2)
                self.assertEqual(calls, 2 if marker_only else 3)
                self.assertEqual(len({row["id"] for row in report["results"]}), len(report["results"]))
                if marker_only:
                    self.assertEqual(client.token, "")
                finish(Path(temporary), report)
                self.assertTrue((Path(temporary) / "views/results.html").is_file())
