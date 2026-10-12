import unittest
from decimal import Decimal

from filbet.loss_rebate import (ContractError, auth_denied, check_key, coverage_features, evidence_status, pages_equal,
                                parse_page, precision_result, public_observation)


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


if __name__ == "__main__":
    unittest.main()
