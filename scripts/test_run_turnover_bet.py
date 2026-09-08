import importlib.util
import os
import json
import sys
import tempfile
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


class TurnoverStopEvidenceTests(unittest.TestCase):
    def test_cap_after_completed_batch_persists_partial_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            original = os.getcwd()
            os.chdir(directory)
            try:
                Path('ui/results').mkdir(parents=True)
                Path('ui/results/client-game-bet-smoke.json').write_text(json.dumps({'completedSpinCount': 18}))
                with patch.object(MODULE, 'load_env_file'), patch.object(MODULE, 'AdminTurnoverReader') as reader, patch.object(MODULE.subprocess, 'run') as ui, patch.dict(os.environ, {'BET_CLIENT_PHONE': '9000000001', 'BET_CLIENT_PASSWORD': 'test-only'}, clear=True), patch.object(sys, 'argv', ['runner', '--env', 'unused', '--execute', '--turnover-source', 'admin', '--bet-unit', '100', '--max-spins', '20', '--poll-timeout', '0']):
                    reader.return_value.unfinished.side_effect = [Decimal('1800'), Decimal('1300')]
                    with self.assertRaisesRegex(SystemExit, '31 exceed safety cap 20'):
                        MODULE.main()
                    self.assertEqual(ui.call_count, 1)
                result = json.loads(Path('ui/results/turnover-bet-plan.json').read_text())
                self.assertEqual(result['completed_spins'], 18)
                self.assertEqual(result['turnover_after'], '1300')
                self.assertFalse(result['turnover_cleared'])
                self.assertTrue(result['stop_reason'])
            finally:
                os.chdir(original)


if __name__ == "__main__":
    unittest.main()
