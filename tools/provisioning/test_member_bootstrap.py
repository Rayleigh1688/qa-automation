from __future__ import annotations

import argparse
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("member-bootstrap.py")
SPEC = importlib.util.spec_from_file_location("member_bootstrap", MODULE_PATH)
assert SPEC and SPEC.loader
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


class MemberBootstrapTest(unittest.TestCase):
    def test_masked_phone_only_exposes_last_four_digits(self) -> None:
        self.assertEqual(bootstrap.masked_phone("9110000005"), "******0005")

    def test_output_directory_must_stay_under_ignored_results(self) -> None:
        with self.assertRaises(bootstrap.ProvisioningError):
            bootstrap.ensure_ignored_output_dir(Path("/tmp/provisioning-output"))

    def test_find_unused_phone_skips_existing_numbers(self) -> None:
        args = argparse.Namespace(start_phone="9110000000", scan_limit=10)

        def exists(_args: argparse.Namespace, phone: str) -> bool:
            return phone in {"9888888000", "9110000000", "9110000001"}

        with patch.dict(os.environ, {"CLIENT_PHONE": "9888888000"}, clear=False):
            with patch.object(bootstrap, "exact_member_exists", side_effect=exists):
                self.assertEqual(bootstrap.find_unused_phone(args), "9110000002")

    def test_find_unused_phone_defaults_to_9000000001(self) -> None:
        args = argparse.Namespace(start_phone="", scan_limit=10)

        def exists(_args: argparse.Namespace, phone: str) -> bool:
            return phone in {"9888888000", "9000000001", "9000000002"}

        with patch.dict(
            os.environ,
            {
                "CLIENT_PHONE": "9888888000",
                "REGISTER_PHONE": "",
                "PROVISION_PHONE_START": "",
            },
            clear=False,
        ):
            with patch.object(bootstrap, "exact_member_exists", side_effect=exists):
                self.assertEqual(bootstrap.find_unused_phone(args), "9000000003")

    def test_find_unused_phone_persists_and_resumes_environment_cursor(self) -> None:
        known = "9888888000"
        existing = {known}
        with tempfile.TemporaryDirectory() as directory:
            cursor = Path(directory) / "register-phone-fat.json"
            args = argparse.Namespace(
                start_phone="",
                scan_limit=10,
                phone_cursor_path=str(cursor),
                env=".env.fat",
            )
            with patch.dict(
                os.environ,
                {
                    "CLIENT_PHONE": known,
                    "REGISTER_PHONE": "",
                    "PROVISION_PHONE_START": "",
                },
                clear=False,
            ):
                with patch.object(
                    bootstrap,
                    "exact_member_exists",
                    side_effect=lambda _args, phone: phone in existing,
                ):
                    first = bootstrap.find_unused_phone(args)
                    self.assertEqual(first, "9000000001")
                    self.assertEqual(bootstrap.load_phone_cursor(cursor), first)
                    existing.add(first)
                    second = bootstrap.find_unused_phone(args)
                    self.assertEqual(second, "9000000002")
                    self.assertEqual(bootstrap.load_phone_cursor(cursor), second)

    def test_required_business_record_blocks_false_status(self) -> None:
        records = [{"name": "register", "business_status": False}]
        with self.assertRaises(bootstrap.ProvisioningError):
            bootstrap.require_business_true(records, "register")

    def test_account_rows_treats_null_as_no_rows(self) -> None:
        self.assertEqual(bootstrap.account_rows(None), [])

    def test_account_rows_keeps_only_objects(self) -> None:
        self.assertEqual(bootstrap.account_rows([{"id": 1}, "bad"]), [{"id": 1}])

    def test_safe_result_record_keeps_business_message_without_body(self) -> None:
        record = bootstrap.safe_result_record(
            "check",
            {"status": 200, "decoded_body": {"status": False, "message": "invalid"}},
        )
        self.assertEqual(record["business_status"], False)
        self.assertEqual(record["message"], "invalid")

    def test_login_password_contract(self) -> None:
        self.assertTrue(bootstrap.valid_login_password("Password1"))
        self.assertFalse(bootstrap.valid_login_password("12345678"))
        self.assertFalse(bootstrap.valid_login_password("password"))
        self.assertFalse(bootstrap.valid_login_password("A1short"))

    def test_wallet_password_contract(self) -> None:
        self.assertEqual(bootstrap.wallet_password_body("123456"), {"pwd": "123456"})

    def test_login_password_request_bodies_match_frontend_contract(self) -> None:
        self.assertEqual(
            bootstrap.login_password_auth_body("9000000000", "63", "otp-1", "123456"),
            {
                "code": "123456",
                "phone": "9000000000",
                "country_code": "63",
                "otp_id": "otp-1",
            },
        )
        self.assertEqual(
            bootstrap.login_password_update_body("otp-1", "123456", "Password1"),
            {"code": "123456", "new_password": "Password1", "otp_id": "otp-1"},
        )

    def test_extension_status_does_not_change_core_stages(self) -> None:
        summary = {"stages": {"register": "PASS", "kyc": "PASS", "deposit": "PASS"}}
        bootstrap.mark_extension(summary, "login_password", "BLOCKED", error="stale")
        self.assertTrue(bootstrap.core_stages_pass(summary))
        self.assertEqual(summary["extensions"]["login_password"]["status"], "BLOCKED")

    def test_environment_filename_must_be_explicitly_non_production(self) -> None:
        with patch.dict(
            os.environ,
            {"API_URL": "https://client.example.test", "ADMIN_URL": "https://admin.example.test"},
            clear=False,
        ):
            with self.assertRaises(bootstrap.ProvisioningError):
                bootstrap.validate_test_environment(Path(".env"))

    def test_deposit_checkpoint_accepts_same_order_and_exact_wallet_delta(self) -> None:
        records = [
            {"name": "deposit_create", "business_status": True, "data": {"order_id": "123"}},
            {"name": "admin_deposit_risk_list", "business_status": True, "matched_order": None},
            {"name": "admin_deposit_manual_success", "business_status": True, "deposit_id": 123},
            {"name": "wallet_before", "business_status": True, "data": {"balance": "0"}},
            {"name": "wallet_after", "business_status": True, "data": {"balance": "1200.00"}},
        ]

        evidence = bootstrap.validate_deposit_checkpoint(records, "1200")

        self.assertTrue(evidence["same_created_order"])
        self.assertEqual(evidence["wallet_balance_delta"], "1200.00")
        self.assertFalse(evidence["pending_list_matched"])

    def test_deposit_checkpoint_blocks_wrong_wallet_delta(self) -> None:
        records = [
            {"name": "deposit_create", "business_status": True, "data": {"order_id": "123"}},
            {"name": "admin_deposit_risk_list", "business_status": True, "matched_order": {}},
            {"name": "admin_deposit_manual_success", "business_status": True, "deposit_id": "123"},
            {"name": "wallet_before", "business_status": True, "data": {"balance": "10"}},
            {"name": "wallet_after", "business_status": True, "data": {"balance": "110"}},
        ]

        with self.assertRaises(bootstrap.ProvisioningError):
            bootstrap.validate_deposit_checkpoint(records, "1200")


if __name__ == "__main__":
    unittest.main()
