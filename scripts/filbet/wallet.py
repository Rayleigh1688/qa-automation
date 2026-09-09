"""FILBET wallet operations on one ControlledFlow instance."""
from __future__ import annotations
import argparse
import os
import time
from .constants import DEFAULT_WITHDRAW_AMOUNT


class WalletOperations:
    def query_wallet(self, args: argparse.Namespace, name: str) -> dict[str, object]:
        result = self.smoke.request_once(
            self.row("GET", "{{api_url}}/finance/wallet"),
            args.timeout,
            args.insecure,
        )
        return self.result_record(name, result)


    def wait_for_deposit_credit(self, 
        args: argparse.Namespace,
        wallet_before: dict[str, object],
        expected_amount: str,
    ) -> dict[str, object]:
        before_data = wallet_before.get("data")
        before_balance = (
            self.decimal_value(before_data.get("balance"))
            if isinstance(before_data, dict)
            else None
        )
        amount = self.decimal_value(expected_amount)
        if before_balance is None or amount is None:
            return {
                "name": "wallet_after_deposit",
                "business_status": False,
                "reason": "deposit wallet checkpoint is not numeric",
            }
        attempts = max(1, int(args.wallet_settlement_attempts))
        interval = max(0.0, float(args.wallet_settlement_interval))
        record: dict[str, object] = {}
        for attempt in range(1, attempts + 1):
            record = self.query_wallet(args, "wallet_after_deposit")
            after_data = record.get("data")
            after_balance = (
                self.decimal_value(after_data.get("balance"))
                if isinstance(after_data, dict)
                else None
            )
            record["expected_balance_delta"] = str(amount)
            record["actual_balance_delta"] = (
                str(after_balance - before_balance) if after_balance is not None else ""
            )
            record["poll_attempts"] = attempt
            if (
                record.get("business_status") is True
                and after_balance is not None
                and after_balance - before_balance >= amount
            ):
                return record
            if attempt < attempts:
                time.sleep(interval)
        record["business_status"] = False
        record["reason"] = (
            f"deposit was approved but wallet balance did not increase by {amount} "
            f"within {attempts} attempts"
        )
        return record


    def wait_for_withdrawable_funds(self, args: argparse.Namespace) -> dict[str, object]:
        required = self.decimal_value(args.withdraw_amount or DEFAULT_WITHDRAW_AMOUNT)
        if required is None or required <= 0:
            return {
                "name": "wallet_before_withdraw",
                "business_status": False,
                "reason": "withdraw amount is not numeric",
            }
        attempts = max(1, int(args.wallet_settlement_attempts))
        interval = max(0.0, float(args.wallet_settlement_interval))
        record: dict[str, object] = {}
        for attempt in range(1, attempts + 1):
            record = self.query_wallet(args, "wallet_before_withdraw")
            data = record.get("data")
            balance = self.decimal_value(data.get("balance")) if isinstance(data, dict) else None
            withdrawable = self.decimal_value(data.get("withdrawable")) if isinstance(data, dict) else None
            record["required_amount"] = str(required)
            record["poll_attempts"] = attempt
            if (
                record.get("business_status") is True
                and balance is not None
                and withdrawable is not None
                and balance >= required
                and withdrawable >= required
            ):
                return record
            if attempt < attempts:
                time.sleep(interval)
        record["business_status"] = False
        record["reason"] = (
            f"wallet does not have withdrawable funds >= {required} after turnover clear"
        )
        return record


    def wallet_password_body(self, password: str) -> dict[str, str]:
        return {"pwd": password}


    def prepare_withdraw_account(self, args: argparse.Namespace) -> list[dict[str, object]]:
        password = args.wallet_password or os.environ.get("CLIENT_WALLET_PASSWORD", "")
        phone = "".join(character for character in os.environ.get("CLIENT_PHONE", "") if character.isdigit())
        maya_account = args.maya_account or os.environ.get("PROVISION_MAYA_ACCOUNT", "") or phone
        maya_pid = args.maya_pid or os.environ.get("PROVISION_MAYA_PID", "")
        if not (password.isdigit() and len(password) == 6):
            raise SystemExit("CLIENT_WALLET_PASSWORD or --wallet-password must be a 6-digit value")
        if not maya_account.isdigit():
            raise SystemExit("Maya account must be numeric")
        if not maya_pid.isdigit():
            raise SystemExit("PROVISION_MAYA_PID or --maya-pid must be numeric")

        records: list[dict[str, object]] = []
        profile = self.smoke.request_once(
            self.row("GET", "{{api_url}}/member/detail"), args.timeout, args.insecure
        )
        profile_record = self.result_record("member_detail_before_withdraw_account", profile)
        records.append(profile_record)
        profile_data = self.data_of(profile)
        if not self.business_ok(profile) or not isinstance(profile_data, dict):
            return records

        has_wallet_password = profile_data.get("has_wallet_password") is True
        profile_record["has_wallet_password"] = has_wallet_password
        if not has_wallet_password:
            password_result = self.smoke.request_once(
                self.row("POST", "{{api_url}}/finance/wallet/pwd/set"),
                args.timeout,
                args.insecure,
                self.wallet_password_body(password),
                args.body_format,
                content_type="application/json",
            )
            records.append(self.result_record("wallet_password_set", password_result))
            if not self.business_ok(password_result):
                return records

        password_check = self.smoke.request_once(
            self.row("POST", "{{api_url}}/finance/wallet/pwd/check"),
            args.timeout,
            args.insecure,
            self.wallet_password_body(password),
            args.body_format,
            content_type="application/json",
        )
        records.append(self.result_record("wallet_password_check", password_check))
        if not self.business_ok(password_check):
            return records

        before = self.smoke.request_once(
            self.row("GET", "{{api_url}}/finance/account/list"), args.timeout, args.insecure
        )
        before_record = self.result_record("withdraw_account_before", before)
        before_rows = self.list_rows(self.data_of(before))
        existing = next(
            (
                item
                for item in before_rows
                if str(item.get("account") or "") == maya_account
                and str(item.get("payment_platform_id") or "") == maya_pid
            ),
            None,
        )
        before_record["matched_account"] = existing is not None
        records.append(before_record)
        if not self.business_ok(before):
            return records

        if existing is None:
            insert = self.smoke.request_once(
                self.row("POST", "{{api_url}}/finance/account/insert"),
                args.timeout,
                args.insecure,
                {
                    "account": maya_account,
                    "first_name": args.maya_first_name,
                    "last_name": args.maya_last_name,
                    "middle_name": args.maya_middle_name,
                    "pid": maya_pid,
                    "cat": 2,
                    "bank_name": None,
                    "bank_code": None,
                },
                args.body_format,
                content_type="application/json",
            )
            records.append(self.result_record("withdraw_account_insert", insert))
            if not self.business_ok(insert):
                return records
        else:
            records.append({
                "name": "withdraw_account_insert",
                "business_status": True,
                "skipped": True,
                "reason": "matching Maya account already exists",
            })

        after = self.smoke.request_once(
            self.row("GET", "{{api_url}}/finance/account/list"), args.timeout, args.insecure
        )
        after_record = self.result_record("withdraw_account_after", after)
        matched = next(
            (
                item
                for item in self.list_rows(self.data_of(after))
                if str(item.get("account") or "") == maya_account
                and str(item.get("payment_platform_id") or "") == maya_pid
            ),
            None,
        )
        account_id = str(matched.get("id") or "") if isinstance(matched, dict) else ""
        after_record.update({
            "matched_account": matched is not None,
            "account_masked": "*" * max(len(maya_account) - 4, 0) + maya_account[-4:],
            "payment_platform_id": maya_pid,
            "account_id": account_id,
        })
        if self.business_ok(after) and not account_id:
            after_record["business_status"] = False
            after_record["reason"] = "Maya account was not returned after binding"
        records.append(after_record)
        return records


