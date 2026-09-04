import argparse
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("api-controlled-flow-runner.py")
SPEC = importlib.util.spec_from_file_location("api_controlled_flow_runner", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def deposit_args(amount: str = "1200", pid: str = "") -> argparse.Namespace:
    return argparse.Namespace(
        timeout=1,
        insecure=True,
        body_format="cbor",
        deposit_amount=amount,
        deposit_pid=pid,
        approve_deposit=True,
    )


def operation_args(operation: str) -> argparse.Namespace:
    values = {flag: False for flag in MODULE.OPERATION_FLAGS.values()}
    return argparse.Namespace(
        operation=operation,
        complete_kyc=False,
        main_positive_flow=False,
        client_phone="",
        client_otp="",
        kyc_uid="",
        deposit_id="",
        deposit_amount="",
        deposit_pid="",
        withdraw_id="",
        withdraw_amount="",
        withdraw_account_id="",
        register_phone="",
        register_scan_limit=200,
        member_uid="",
        env=".env.fat",
        out="",
        **values,
    )


class DepositChannelTests(unittest.TestCase):
    def test_selects_channel_whose_range_and_amount_tier_accept_request(self):
        response = {
            "decoded_body": {
                "status": True,
                "data": [
                    {"id": "first", "min_amount": "50", "max_amount": "1000", "amount_limit": ["100", "500"]},
                    {"id": "matching", "min_amount": "100", "max_amount": "5000", "amount_limit": ["1000", "2000"]},
                ],
            }
        }
        with patch.object(MODULE.smoke, "request_once", return_value=response):
            self.assertEqual(MODULE.choose_deposit_channel(deposit_args()), ("matching", "1200"))

    def test_rejects_configured_channel_when_amount_is_outside_range(self):
        response = {
            "decoded_body": {
                "status": True,
                "data": [{"id": "fixed", "min_amount": "50", "max_amount": "1000", "amount_limit": ["500", "1000"]}],
            }
        }
        with patch.object(MODULE.smoke, "request_once", return_value=response):
            with self.assertRaisesRegex(SystemExit, "no deposit channel accepts amount=1200"):
                MODULE.choose_deposit_channel(deposit_args(pid="fixed"))


class DepositFailFastTests(unittest.TestCase):
    def test_wallet_credit_poll_waits_for_expected_deposit_delta(self):
        args = argparse.Namespace(wallet_settlement_attempts=3, wallet_settlement_interval=0)
        before = {"data": {"balance": "10"}}
        responses = [
            {"name": "wallet_after_deposit", "business_status": True, "data": {"balance": "10"}},
            {"name": "wallet_after_deposit", "business_status": True, "data": {"balance": "1210"}},
        ]
        with patch.object(MODULE, "query_wallet", side_effect=responses) as query:
            record = MODULE.wait_for_deposit_credit(args, before, "1200")
        self.assertEqual(query.call_count, 2)
        self.assertTrue(record["business_status"])
        self.assertEqual(record["actual_balance_delta"], "1200")

    def test_wallet_credit_poll_blocks_before_turnover_when_credit_never_arrives(self):
        args = argparse.Namespace(wallet_settlement_attempts=2, wallet_settlement_interval=0)
        before = {"data": {"balance": "0"}}
        response = {
            "name": "wallet_after_deposit",
            "business_status": True,
            "data": {"balance": "0"},
        }
        with patch.object(MODULE, "query_wallet", return_value=response):
            record = MODULE.wait_for_deposit_credit(args, before, "1200")
        self.assertFalse(record["business_status"])
        self.assertIn("did not increase", record["reason"])

    def test_withdraw_waits_until_balance_and_withdrawable_are_sufficient(self):
        args = argparse.Namespace(
            withdraw_amount="100",
            wallet_settlement_attempts=3,
            wallet_settlement_interval=0,
        )
        responses = [
            {"name": "wallet_before_withdraw", "business_status": True, "data": {"balance": "1200", "withdrawable": "0"}},
            {"name": "wallet_before_withdraw", "business_status": True, "data": {"balance": "1200", "withdrawable": "1200"}},
        ]
        with patch.object(MODULE, "query_wallet", side_effect=responses) as query:
            record = MODULE.wait_for_withdrawable_funds(args)
        self.assertEqual(query.call_count, 2)
        self.assertTrue(record["business_status"])

    def test_business_failure_stops_before_admin_list_and_approval(self):
        records = []
        failed = [{"name": "deposit_create", "http_status": 200, "business_status": False}]
        with (
            patch.object(MODULE, "run_deposit", return_value=failed),
            patch.object(MODULE, "find_deposit_order") as find_order,
            patch.object(MODULE, "approve_deposit") as approve,
        ):
            self.assertFalse(MODULE.run_deposit_stage(deposit_args(), records))
        self.assertEqual(records, failed)
        find_order.assert_not_called()
        approve.assert_not_called()

    def test_success_uses_exact_client_identifiers_for_approval(self):
        args = deposit_args()
        records = []
        created = [{
            "name": "deposit_create",
            "http_status": 200,
            "business_status": True,
            "data": {"order_id": "deposit-1"},
            "external_order_id": "external-1",
        }]
        client = [{
            "name": "client_deposit_list",
            "business_status": True,
            "matched_order": {"external_order_id": "external-1"},
        }]
        approved = [{"name": "admin_deposit_manual_success", "business_status": True}]
        with (
            patch.object(MODULE, "run_deposit", return_value=created),
            patch.object(MODULE, "check_client_deposit_list", return_value=client),
            patch.object(MODULE, "approve_deposit", return_value=approved) as approve,
        ):
            self.assertTrue(MODULE.run_deposit_stage(args, records))
        approve.assert_called_once_with(args, None, "deposit-1", "external-1")
        self.assertEqual(
            [item["name"] for item in records],
            ["deposit_create", "client_deposit_list", "admin_deposit_manual_success"],
        )


class IndependentOperationTests(unittest.TestCase):
    def tearDown(self):
        MODULE.LAST_APPROVAL_CODE = ""

    def test_dynamic_approval_secret_takes_precedence_over_stale_env_code(self):
        args = argparse.Namespace(approval_code="")
        with (
            patch.dict(
                os.environ,
                {
                    "ADMIN_APPROVAL_CODE": "000000",
                    "ADMIN_APPROVAL_TOTP_SECRET": "secret",
                    "ADMIN_APPROVAL_TOTP_ALGORITHM": "SHA256",
                },
                clear=True,
            ),
            patch.object(MODULE, "current_totp", return_value="123456") as totp,
            patch.object(MODULE.time, "time", return_value=10),
        ):
            self.assertEqual(MODULE.approval_code(args), "123456")
        totp.assert_called_once_with("secret", algorithm="SHA256")

    def test_repeated_totp_waits_for_a_new_approval_window(self):
        args = argparse.Namespace(approval_code="")
        MODULE.LAST_APPROVAL_CODE = "123456"
        with (
            patch.dict(
                os.environ,
                {"ADMIN_APPROVAL_TOTP_SECRET": "secret"},
                clear=True,
            ),
            patch.object(MODULE, "current_totp", side_effect=["123456", "654321"]),
            patch.object(MODULE.time, "time", side_effect=[10, 10]),
            patch.object(MODULE.time, "sleep") as sleep,
        ):
            self.assertEqual(MODULE.approval_code(args), "654321")
        sleep.assert_called_once_with(21)

    def test_withdraw_business_failure_stops_stage_without_business_id(self):
        args = argparse.Namespace(
            withdraw_amount="100",
            withdraw_lookup_attempts=1,
            withdraw_lookup_interval=0,
        )
        records = []
        failed = [{"name": "withdraw_create", "http_status": 200, "business_status": False}]
        list_result = {"status": 200, "decoded_body": {"status": True, "data": {"d": []}}}
        with (
            patch.object(MODULE, "run_withdraw", return_value=failed),
            patch.object(MODULE, "fetch_client_withdraw_list", return_value=(list_result, [])),
        ):
            succeeded, withdraw_id = MODULE.run_withdraw_stage(args, records)
        self.assertFalse(succeeded)
        self.assertEqual(withdraw_id, "")
        self.assertEqual(records[-1]["name"], "client_withdraw_async_reconcile")

    def test_withdraw_success_requires_business_id_for_exact_follow_up(self):
        args = argparse.Namespace(
            withdraw_amount="100",
            withdraw_lookup_attempts=1,
            withdraw_lookup_interval=0,
        )
        records = []
        successful_without_id = [
            {"name": "withdraw_create", "http_status": 200, "business_status": True, "data": {}}
        ]
        list_result = {"status": 200, "decoded_body": {"status": True, "data": {"d": []}}}
        with (
            patch.object(MODULE, "run_withdraw", return_value=successful_without_id),
            patch.object(MODULE, "fetch_client_withdraw_list", return_value=(list_result, [])),
        ):
            succeeded, withdraw_id = MODULE.run_withdraw_stage(args, records)
        self.assertFalse(succeeded)
        self.assertEqual(withdraw_id, "")
        self.assertEqual(records[-1]["name"], "client_withdraw_async_reconcile")

    def test_withdraw_false_response_is_reconciled_by_one_new_matching_order(self):
        args = argparse.Namespace(
            withdraw_amount="100",
            withdraw_lookup_attempts=2,
            withdraw_lookup_interval=0,
        )
        before_result = {"status": 200, "decoded_body": {"status": True, "data": {"d": []}}}
        after_result = {"status": 200, "decoded_body": {"status": True, "data": {"d": []}}}
        failed = [{
            "name": "withdraw_create",
            "http_status": 200,
            "business_status": False,
            "amount": "100",
            "selected_account": {"payment_platform_id": "maya-pid"},
        }]
        new_order = {
            "id": "withdraw-1",
            "amount": "100.00000000",
            "payment_platform_id": "maya-pid",
            "created_at": int(MODULE.time.time() * 1000),
            "status": "paying",
        }
        records = []
        with (
            patch.object(MODULE, "run_withdraw", return_value=failed),
            patch.object(
                MODULE,
                "fetch_client_withdraw_list",
                side_effect=[(before_result, []), (after_result, [new_order])],
            ),
        ):
            succeeded, withdraw_id = MODULE.run_withdraw_stage(args, records)
        self.assertTrue(succeeded)
        self.assertEqual(withdraw_id, "withdraw-1")
        self.assertTrue(records[1]["async_reconciled"])
        self.assertEqual(records[1]["response_business_status"], False)

    def test_paying_withdraw_skips_manual_admin_agree(self):
        args = argparse.Namespace()
        records = MODULE.approve_withdraw(args, {"id": "withdraw-1", "status": "paying"})
        self.assertTrue(records[0]["business_status"])
        self.assertTrue(records[0]["skipped"])

    def test_prepare_maya_account_defaults_account_to_logged_in_phone(self):
        args = argparse.Namespace(
            wallet_password="",
            maya_account="",
            maya_pid="47870583692853381",
            maya_first_name="Codex",
            maya_middle_name="",
            maya_last_name="001",
            timeout=1,
            insecure=True,
            body_format="cbor",
        )
        responses = [
            {"status": 200, "decoded_body": {"status": True, "data": {"has_wallet_password": True}}},
            {"status": 200, "decoded_body": {"status": True, "data": None}},
            {"status": 200, "decoded_body": {"status": True, "data": []}},
            {"status": 200, "decoded_body": {"status": True, "data": None}},
            {
                "status": 200,
                "decoded_body": {
                    "status": True,
                    "data": [{
                        "id": "account-id",
                        "account": "9000000016",
                        "payment_platform_id": "47870583692853381",
                    }],
                },
            },
        ]
        with (
            patch.dict(
                os.environ,
                {"CLIENT_PHONE": "9000000016", "CLIENT_WALLET_PASSWORD": "123456"},
                clear=True,
            ),
            patch.object(MODULE.smoke, "request_once", side_effect=responses) as request,
        ):
            records = MODULE.prepare_withdraw_account(args)

        insert_call = request.call_args_list[3]
        self.assertEqual(insert_call.args[3]["account"], "9000000016")
        self.assertEqual(insert_call.args[3]["pid"], "47870583692853381")
        self.assertEqual(records[-1]["account_id"], "account-id")
        self.assertTrue(records[-1]["business_status"])

    def test_prepare_maya_account_rejects_missing_pid_before_requests(self):
        args = argparse.Namespace(
            wallet_password="123456",
            maya_account="",
            maya_pid="",
            maya_first_name="Codex",
            maya_middle_name="",
            maya_last_name="001",
            timeout=1,
            insecure=True,
            body_format="cbor",
        )
        with (
            patch.dict(os.environ, {"CLIENT_PHONE": "9000000016"}, clear=True),
            patch.object(MODULE.smoke, "request_once") as request,
        ):
            with self.assertRaisesRegex(SystemExit, "MAYA_PID|maya-pid"):
                MODULE.prepare_withdraw_account(args)
        request.assert_not_called()

    def test_withdraw_defaults_to_confirmed_minimum_100(self):
        args = argparse.Namespace(
            withdraw_account_id="",
            withdraw_amount="",
            timeout=1,
            insecure=True,
        )
        response = {
            "decoded_body": {
                "status": True,
                "data": [{
                    "id": "maya-1",
                    "status": 1,
                    "min_amount": "1",
                    "max_amount": "10000",
                    "amount_limit": ["1", "10", "100"],
                }],
            },
        }
        with patch.object(MODULE.smoke, "request_once", return_value=response):
            account_id, amount, _ = MODULE.choose_withdraw_account(args)
        self.assertEqual(account_id, "maya-1")
        self.assertEqual(amount, "100")

    def test_register_phone_lane_ignores_stale_environment_kyc_uid(self):
        args = argparse.Namespace(
            kyc_uid="",
            use_register_phone=True,
        )
        with patch.dict(os.environ, {"KYC_CLIENT_UID": "stale-uid"}, clear=True):
            uid = MODULE.resolve_kyc_uid(args, {"uid": "current-uid"})
        self.assertEqual(uid, "current-uid")

    def test_kyc_approval_uses_frontend_comment_field(self):
        args = argparse.Namespace(
            timeout=1,
            insecure=True,
            body_format="cbor",
            approval_desc="p0 approval",
            approval_code="123456",
        )
        approved_response = {"status": 200, "decoded_body": {"status": True, "data": None}}
        detail_response = {
            "status": 200,
            "decoded_body": {"status": True, "data": {"kyc_status": 5}},
        }
        with (
            patch.object(
                MODULE,
                "find_kyc_record",
                return_value=(
                    {"name": "admin_kyc_list", "business_status": True},
                    {"uid": "uid-1"},
                ),
            ),
            patch.object(MODULE.smoke, "request_once", return_value=approved_response) as request,
            patch.object(MODULE, "wait_for_kyc_status", return_value=(detail_response, {"kyc_status": 5}, 1)),
        ):
            records = MODULE.approve_kyc(args, "uid-1")
        body = request.call_args.args[3]
        self.assertEqual(body["comment"], "p0 approval")
        self.assertNotIn("desc", body)
        self.assertTrue(records[-1]["business_status"])

    def test_kyc_status_wait_polls_until_approved(self):
        args = argparse.Namespace(
            timeout=1,
            insecure=True,
            kyc_status_attempts=3,
            kyc_status_interval=0,
        )
        pending = {"decoded_body": {"status": True, "data": {"kyc_status": 2}}}
        approved = {"decoded_body": {"status": True, "data": {"kyc_status": 5}}}
        with patch.object(MODULE.smoke, "request_once", side_effect=[pending, approved]) as request:
            _, profile, attempts = MODULE.wait_for_kyc_status(args, 5)
        self.assertEqual(request.call_count, 2)
        self.assertEqual(profile["kyc_status"], 5)
        self.assertEqual(attempts, 2)

    def test_result_record_redacts_token_from_data_and_body_sample(self):
        record = MODULE.result_record(
            "register",
            {
                "status": 200,
                "decoded_body": {"status": True, "data": {"token": "secret-token"}},
            },
        )
        self.assertEqual(record["data"]["token"], "<redacted>")
        self.assertNotIn("secret-token", record["body_sample"])

    def test_registration_allocator_resumes_from_environment_cursor(self):
        args = operation_args("register")
        known = "9888888000"
        existing = {known}
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(MODULE, "PHONE_CURSOR_DIR", Path(directory)),
                patch.dict(
                    os.environ,
                    {
                        "CLIENT_PHONE": known,
                        "REGISTER_PHONE": "",
                        "PROVISION_PHONE_START": "",
                    },
                    clear=True,
                ),
                patch.object(
                    MODULE,
                    "admin_member_exists",
                    side_effect=lambda _args, phone: phone in existing,
                ),
            ):
                first, _ = MODULE.allocate_registration_phone(args)
                self.assertEqual(first, "9000000001")
                cursor = MODULE.phone_cursor_path(args.env)
                self.assertEqual(MODULE.load_phone_cursor(cursor), first)

                existing.add(first)
                second, record = MODULE.allocate_registration_phone(args)
                self.assertEqual(second, "9000000002")
                self.assertEqual(MODULE.load_phone_cursor(cursor), second)
                self.assertEqual(record["checked_candidates"], 2)

    def test_deposit_create_uses_write_lane_and_only_enables_deposit(self):
        args = operation_args("deposit-create")
        env = {
            "WRITE_CLIENT_PHONE": "09000000001",
            "WRITE_CLIENT_PASSWORD": "password",
            "WRITE_CLIENT_OTP": "111111",
        }
        with patch.dict(os.environ, env, clear=True):
            MODULE.configure_operation(args)
            self.assertTrue(args.deposit)
            self.assertFalse(args.approve_deposit)
            self.assertEqual(os.environ["CLIENT_PHONE"], env["WRITE_CLIENT_PHONE"])
            self.assertEqual(os.environ["CLIENT_PASSWORD"], env["WRITE_CLIENT_PASSWORD"])

    def test_operation_rejects_legacy_flow_flags(self):
        args = operation_args("deposit-create")
        args.withdraw = True
        with self.assertRaisesRegex(SystemExit, "cannot be combined"):
            MODULE.configure_operation(args)

    def test_withdraw_create_uses_configured_p0_amount(self):
        args = operation_args("withdraw-create")
        env = {
            "WITHDRAW_CLIENT_PHONE": "09000000002",
            "WITHDRAW_CLIENT_PASSWORD": "password",
            "P0_WITHDRAW_AMOUNT": "1000",
        }
        with patch.dict(os.environ, env, clear=True):
            MODULE.configure_operation(args)
        self.assertEqual(args.withdraw_amount, "1000")

    def test_admin_order_operations_require_explicit_business_id(self):
        for operation in (
            "deposit-check-client",
            "deposit-check-admin",
            "deposit-approve",
            "withdraw-check-admin",
            "withdraw-approve",
        ):
            with self.subTest(operation=operation):
                args = operation_args(operation)
                with patch.dict(os.environ, {}, clear=True):
                    with self.assertRaisesRegex(SystemExit, "requires"):
                        MODULE.configure_operation(args)

    def test_turnover_clear_operation_requires_member_uid(self):
        args = operation_args("turnover-clear")
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(SystemExit, "member-uid"):
                MODULE.configure_operation(args)

    def test_turnover_clear_uses_frontend_cbor_content_type_and_verifies_zero(self):
        args = argparse.Namespace(
            timeout=1,
            insecure=True,
            approval_code="123456",
            turnover_clear_remark="test",
        )
        before = {
            "status": 200,
            "decoded_body": {
                "status": True,
                "data": {"d": [{"state": 1, "turnover": "1200", "finished": "0"}]},
            },
        }
        cleared = {"status": 200, "decoded_body": {"status": True, "data": "ok"}}
        after = {
            "status": 200,
            "decoded_body": {"status": True, "data": {"d": []}},
        }
        with patch.object(MODULE.smoke, "request_once", side_effect=[before, cleared, after]) as request:
            records = MODULE.run_turnover_clear(args, "uid-1")
        self.assertEqual([item["business_status"] for item in records], [True, True, True])
        self.assertEqual(records[-1]["remaining_turnover"], "0")
        self.assertEqual(
            request.call_args_list[1].kwargs["content_type"],
            "application/x-www-form-urlencoded",
        )

    def test_turnover_clear_polls_until_admin_state_reaches_zero(self):
        args = argparse.Namespace(
            timeout=1,
            insecure=True,
            body_format="cbor",
            turnover_clear_remark="test",
            approval_code="111111",
            turnover_clear_attempts=3,
            turnover_clear_interval=0,
        )
        responses = [
            ({"name": "turnover_before_clear", "business_status": True}, MODULE.Decimal("1800")),
            ({"name": "turnover_after_clear", "business_status": True}, MODULE.Decimal("1800")),
            ({"name": "turnover_after_clear", "business_status": True}, MODULE.Decimal("0")),
        ]
        clear_result = {"status": 200, "decoded_body": {"status": True, "data": {"affected": 1}}}
        with (
            patch.object(MODULE, "query_admin_turnover", side_effect=responses) as query,
            patch.object(MODULE.smoke, "request_once", return_value=clear_result),
        ):
            records = MODULE.run_turnover_clear(args, "uid-1")
        self.assertEqual(query.call_count, 3)
        self.assertTrue(records[-1]["business_status"])
        self.assertEqual(records[-1]["poll_attempts"], 2)

    def test_locked_wallet_waits_for_delayed_turnover_record_before_clear(self):
        args = argparse.Namespace(
            timeout=1,
            insecure=True,
            body_format="cbor",
            turnover_clear_remark="test",
            approval_code="111111",
            turnover_discovery_attempts=3,
            turnover_discovery_interval=0,
            turnover_clear_attempts=1,
            turnover_clear_interval=0,
        )
        responses = [
            ({"name": "turnover_before_clear", "business_status": True, "row_count": 0}, MODULE.Decimal("0")),
            ({"name": "turnover_before_clear", "business_status": True, "row_count": 1}, MODULE.Decimal("1800")),
            ({"name": "turnover_after_clear", "business_status": True, "row_count": 1}, MODULE.Decimal("0")),
        ]
        clear_result = {"status": 200, "decoded_body": {"status": True, "data": {"affected": 1}}}
        with (
            patch.object(MODULE, "query_admin_turnover", side_effect=responses) as query,
            patch.object(MODULE.smoke, "request_once", return_value=clear_result),
        ):
            records = MODULE.run_turnover_clear(args, "uid-1", MODULE.Decimal("1800"))
        self.assertEqual(query.call_count, 3)
        self.assertEqual(records[0]["row_count"], 1)
        self.assertTrue(records[-1]["business_status"])

    def test_client_withdraw_check_requires_explicit_business_id(self):
        args = operation_args("withdraw-check-client")
        with patch.dict(
            os.environ,
            {"WITHDRAW_CLIENT_PHONE": "09000000002", "WITHDRAW_CLIENT_PASSWORD": "password"},
            clear=True,
        ):
            with self.assertRaisesRegex(SystemExit, "withdraw-id"):
                MODULE.configure_operation(args)

    def test_deposit_lookup_does_not_fall_back_to_another_order(self):
        args = argparse.Namespace(
            deposit_status="",
            timeout=1,
            insecure=True,
            body_format="cbor",
        )
        response = {
            "url": "https://admin.example/admin/finance/deposit/risk/list",
            "status": 200,
            "decoded_body": {"status": True, "data": {"d": [{"id": "other"}]}},
        }
        with patch.object(MODULE.smoke, "request_once", return_value=response):
            record, target = MODULE.find_deposit_order(args, "expected")
        self.assertIsNone(target)
        self.assertFalse(record["business_status"])
        self.assertIn("expected", record["reason"])

    def test_deposit_lookup_retries_unfiltered_and_matches_client_order_id(self):
        args = argparse.Namespace(
            deposit_status="",
            deposit_lookup_attempts=2,
            deposit_lookup_interval=0,
            timeout=1,
            insecure=True,
            body_format="cbor",
        )
        empty = {
            "url": "https://admin.example/admin/finance/deposit/risk/list",
            "status": 200,
            "decoded_body": {"status": True, "data": {"d": []}},
        }
        matched = {
            "url": "https://admin.example/admin/finance/deposit/risk/list",
            "status": 200,
            "decoded_body": {
                "status": True,
                "data": {"d": [{"id": "internal", "order_id": "client-order"}]},
            },
        }
        with patch.object(MODULE.smoke, "request_once", side_effect=[empty, matched]) as request:
            record, target = MODULE.find_deposit_order(args, "client-order")
        self.assertEqual(request.call_count, 2)
        self.assertEqual(target["id"], "internal")
        self.assertTrue(record["business_status"])

    def test_operation_finish_writes_json_and_html_report(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "deposit-create.json"
            args = argparse.Namespace(
                out=str(output),
                operation="deposit-create",
                env=".env.fat",
            )
            MODULE.finish(args, [{
                "name": "deposit_create",
                "url": "https://api.example/finance/payment/deposit?token=secret",
                "http_status": 200,
                "business_status": True,
                "elapsed_ms": 8,
            }])
            self.assertTrue(output.is_file())
            report = output.with_suffix(".html").read_text(encoding="utf-8")
            self.assertIn("deposit-create", report)
            self.assertNotIn("token=secret", report)


if __name__ == "__main__":
    unittest.main()
