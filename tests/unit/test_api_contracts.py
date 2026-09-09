from support import ROOT, SCRIPTS
import csv
import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from api_contracts import WITHDRAW_AUDIT_PATH, normalize_request_template, resolve_dynamic_values


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), (SCRIPTS / (name + ".py")))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RequestContractTests(unittest.TestCase):
    def test_curated_audit_request_uses_milliseconds_in_runner(self):
        smoke = load_script("api-smoke-runner")
        path = ROOT / "api/p0/test-cases.csv"
        with path.open(newline="") as handle:
            case = next(row for row in csv.DictReader(handle) if row["case_id"] == "TC-026")
        with patch.object(smoke.time, "time", return_value=1_800_000_000):
            body = smoke.request_body_for(case)
        self.assertEqual(body["start_time"], 1_799_827_200_000)
        self.assertEqual(body["end_time"], 1_800_000_300_000)
        self.assertEqual(body["status"], "under_review")

    def test_generator_repairs_legacy_template_without_changing_other_endpoints(self):
        builder = load_script("build-p0-test-cases")
        raw = '{"start_time":"{{now_minus_2d}}","end_time":"{{now_plus_5m}}"}'
        rows = [{"path": path, "execution_policy": "safe_smoke", "request_body": raw}
                for path in (WITHDRAW_AUDIT_PATH, "/admin/finance/withdraw/list")]
        cases = builder.normalized_safe_cases(rows)
        audit = json.loads(cases[0]["request_body"])
        self.assertEqual(audit["start_time"], "{{now_minus_2d_ms}}")
        self.assertEqual(cases[1]["request_body"], raw)
        self.assertEqual(normalize_request_template(WITHDRAW_AUDIT_PATH, cases[0]["request_body"]), cases[0]["request_body"])

    def test_ledger_window_is_milliseconds(self):
        body = normalize_request_template('/admin/finance/transaction/list', '{"start_time":"{{now_minus_2d}}","end_time":"{{now_plus_5m}}"}')
        resolved = resolve_dynamic_values(json.loads(body), 1_800_000_000)
        self.assertEqual(resolved['start_time'], 1_799_827_200_000)

    def test_nested_data_keeps_types_and_seconds(self):
        body = {"start_time": "{{now_minus_2d}}", "filters": [{"active": True}], "page": 1, "empty": None}
        resolved = resolve_dynamic_values(body, 1_800_000_000)
        self.assertEqual(resolved["start_time"], 1_799_827_200)
        self.assertEqual(resolved["filters"], [{"active": True}])
        self.assertIsNone(resolved["empty"])
        self.assertEqual(body["start_time"], "{{now_minus_2d}}")


if __name__ == "__main__":
    unittest.main()
