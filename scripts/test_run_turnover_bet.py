import importlib.util
import os
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("run-turnover-bet.py")
SPEC = importlib.util.spec_from_file_location("run_turnover_bet", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class TurnoverSourceTests(unittest.TestCase):
    def test_uat_defaults_to_admin(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(MODULE.choose_turnover_source("auto", ".env.uat"), "admin")

    def test_configured_auto_still_infers_uat(self):
        with patch.dict(os.environ, {"TURNOVER_SOURCE": "auto"}, clear=True):
            self.assertEqual(MODULE.choose_turnover_source("auto", ".env.uat"), "admin")

    def test_fat_defaults_to_database(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(MODULE.choose_turnover_source("auto", ".env.fat"), "database")

    def test_explicit_source_wins(self):
        with patch.dict(os.environ, {"TURNOVER_SOURCE": "database"}, clear=True):
            self.assertEqual(MODULE.choose_turnover_source("admin", ".env.uat"), "admin")


class TurnoverCalculationTests(unittest.TestCase):
    def test_sums_only_unfinished_active_rows(self):
        rows = [
            {"state": 1, "turnover": "480.00", "finished": "130.00"},
            {"state": 1, "turnover": "200", "finished": "50"},
            {"state": 2, "turnover": "999", "finished": "0"},
            {"state": 1, "turnover": "10", "finished": "20"},
        ]
        self.assertEqual(MODULE.remaining_turnover(rows), Decimal("500.00"))

    def test_finds_only_exact_normalized_phone(self):
        payload = {"d": [{"phone": "90000000010", "uid": "wrong"}, {"phone": "9000000001", "uid": "right"}]}
        self.assertEqual(MODULE.find_exact_member(payload, "9000 000 001")["uid"], "right")


if __name__ == "__main__":
    unittest.main()
