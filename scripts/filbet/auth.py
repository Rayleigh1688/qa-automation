"""FILBET auth operations on one ControlledFlow instance."""
from __future__ import annotations
import argparse
import os
from .constants import OPERATION_FLAGS, CLIENT_OPERATION_LANES


class AuthOperations:
    def admin_login(self, args: argparse.Namespace) -> list[dict[str, object]]:
        if os.environ.get("ADMIN_TOKEN"):
            probe = self.smoke.request_once(
                self.row("GET", "{{admin_url}}/admin/me/detail", "{{admin_url}}"),
                args.timeout,
                args.insecure,
            )
            if self.business_ok(probe):
                return [self.result_record("admin_token_reuse", probe)]
            os.environ.pop("ADMIN_TOKEN", None)
        login_results, token = self.smoke.admin_login(args)
        if not token:
            raise SystemExit("admin login failed; cannot run admin approval probes")
        os.environ["ADMIN_TOKEN"] = token
        return [self.result_record("admin_auth", item) for item in login_results[:1]] + [
            self.result_record("admin_login", item) for item in login_results[1:]
        ]


    def client_login(self, args: argparse.Namespace) -> list[dict[str, object]]:
        # Controlled phases may run back-to-back on the same FAT account. Reuse a
        # freshly obtained token when supplied, but validate it before any write so
        # repeated SMS requests do not trigger the test-environment phone limiter.
        if os.environ.get("API_TOKEN"):
            probe = self.smoke.request_once(
                self.row("GET", "{{api_url}}/member/detail"),
                args.timeout,
                args.insecure,
            )
            if self.business_ok(probe):
                return [self.result_record("client_token_reuse", probe)]
            os.environ.pop("API_TOKEN", None)

        login_results, token = self.smoke.client_login(args)
        if not token:
            raise SystemExit("client login failed; cannot run controlled write probes")
        os.environ["API_TOKEN"] = token
        records = []
        for item in login_results:
            url = str(item.get("url") or "")
            if url.endswith("/member/sms"):
                name = "client_sms"
            elif "/member/otp/login" in url:
                name = "client_otp_login"
            else:
                name = "client_password_login"
            records.append(self.result_record(name, item))
        return records


    def relabel(self, records: list[dict[str, object]], prefix: str) -> list[dict[str, object]]:
        renamed = []
        for record in records:
            item = dict(record)
            item["name"] = f"{prefix}_{item.get('name', '')}"
            renamed.append(item)
        return renamed


    def use_withdraw_client(self, 
        args: argparse.Namespace,
    ) -> tuple[str | None, str | None, str | None, str | None]:
        phone = args.withdraw_client_phone or os.environ.get("WITHDRAW_CLIENT_PHONE", "")
        if not phone:
            return None, None, None, None
        previous_phone = os.environ.get("CLIENT_PHONE")
        previous_password = os.environ.get("CLIENT_PASSWORD")
        previous_otp = os.environ.get("CLIENT_OTP")
        previous_token = os.environ.get("API_TOKEN")
        os.environ["CLIENT_PHONE"] = phone
        password = os.environ.get("WITHDRAW_CLIENT_PASSWORD") or os.environ.get("WRITE_CLIENT_PASSWORD", "")
        if password:
            os.environ["CLIENT_PASSWORD"] = password
        otp = args.withdraw_client_otp or os.environ.get("WITHDRAW_CLIENT_OTP", "")
        if otp:
            os.environ["CLIENT_OTP"] = otp
        os.environ.pop("API_TOKEN", None)
        return previous_phone, previous_password, previous_otp, previous_token


    def restore_client(self, 
        previous_phone: str | None,
        previous_password: str | None,
        previous_otp: str | None,
        previous_token: str | None,
    ) -> None:
        if previous_phone is None:
            os.environ.pop("CLIENT_PHONE", None)
        else:
            os.environ["CLIENT_PHONE"] = previous_phone
        if previous_password is None:
            os.environ.pop("CLIENT_PASSWORD", None)
        else:
            os.environ["CLIENT_PASSWORD"] = previous_password
        if previous_otp is None:
            os.environ.pop("CLIENT_OTP", None)
        else:
            os.environ["CLIENT_OTP"] = previous_otp
        if previous_token is None:
            os.environ.pop("API_TOKEN", None)
        else:
            os.environ["API_TOKEN"] = previous_token


    def apply_primary_client_override(self, args: argparse.Namespace) -> None:
        if args.use_register_phone:
            phone = self.load_phone_cursor(self.phone_cursor_path(args.env))
            password = os.environ.get("REGISTER_PASSWORD", "")
            if not phone or not password:
                raise SystemExit("register phone cursor and REGISTER_PASSWORD are required")
            args.client_phone = phone
            os.environ["CLIENT_PHONE"] = phone
            os.environ["CLIENT_PASSWORD"] = password
            otp = os.environ.get("REGISTER_OTP", "")
            if otp:
                os.environ["CLIENT_OTP"] = otp
            return
        phone = args.client_phone or os.environ.get("WRITE_CLIENT_PHONE", "")
        write_phone = os.environ.get("WRITE_CLIENT_PHONE", "")
        normalized_phone = "".join(character for character in phone if character.isdigit())
        normalized_write_phone = "".join(character for character in write_phone if character.isdigit())
        use_write_lane = bool(
            not args.client_phone
            or (normalized_phone and normalized_phone == normalized_write_phone)
        )
        password = os.environ.get("WRITE_CLIENT_PASSWORD", "") if use_write_lane else ""
        otp = args.client_otp or os.environ.get("WRITE_CLIENT_OTP", "")
        if phone:
            os.environ["CLIENT_PHONE"] = phone
        if password:
            os.environ["CLIENT_PASSWORD"] = password
        if otp:
            os.environ["CLIENT_OTP"] = otp


    def apply_operation_client_lane(self, args: argparse.Namespace) -> None:
        prefix = CLIENT_OPERATION_LANES.get(args.operation, "")
        if not prefix:
            return
        phone = os.environ.get(f"{prefix}_PHONE", "")
        password = os.environ.get(f"{prefix}_PASSWORD", "")
        otp = os.environ.get(f"{prefix}_OTP", "")
        if not phone:
            raise SystemExit(f"{prefix}_PHONE is required for operation {args.operation}")
        args.client_phone = phone
        if otp:
            args.client_otp = otp
        os.environ["CLIENT_PHONE"] = phone
        if password:
            os.environ["CLIENT_PASSWORD"] = password
        if otp:
            os.environ["CLIENT_OTP"] = otp


    def configure_operation(self, args: argparse.Namespace) -> None:
        if not args.operation:
            return
        selected = [flag for flag in OPERATION_FLAGS.values() if getattr(args, flag)]
        if selected or args.complete_kyc or args.main_positive_flow:
            raise SystemExit("--operation cannot be combined with legacy flow flags")
        setattr(args, OPERATION_FLAGS[args.operation], True)
        if args.operation == "deposit-create":
            args.deposit_amount = args.deposit_amount or os.environ.get("P0_DEPOSIT_AMOUNT", "")
            args.deposit_pid = args.deposit_pid or os.environ.get("P0_DEPOSIT_PID", "")
        if args.operation == "kyc-submit":
            args.kyc_image = os.environ.get("KYC_IMAGE", "") or args.kyc_image
        if args.operation == "withdraw-create":
            args.withdraw_amount = args.withdraw_amount or os.environ.get("P0_WITHDRAW_AMOUNT", "")
            args.withdraw_account_id = (
                args.withdraw_account_id or os.environ.get("P0_WITHDRAW_ACCOUNT_ID", "")
            )
        if args.operation == "withdraw-account-prepare":
            args.maya_pid = args.maya_pid or os.environ.get("PROVISION_MAYA_PID", "")
        if args.operation == "kyc-approve" and not args.kyc_uid:
            args.kyc_uid = os.environ.get("KYC_CLIENT_UID", "")
            if not args.kyc_uid:
                raise SystemExit("kyc-approve requires --kyc-uid or KYC_CLIENT_UID")
        if args.operation in {
            "deposit-check-client",
            "deposit-check-admin",
            "deposit-approve",
        } and not args.deposit_id:
            args.deposit_id = os.environ.get("P0_DEPOSIT_ID", "")
            if not args.deposit_id:
                raise SystemExit(f"{args.operation} requires --deposit-id or P0_DEPOSIT_ID")
        if args.operation in {
            "withdraw-check-client",
            "withdraw-check-admin",
            "withdraw-approve",
        } and not args.withdraw_id:
            args.withdraw_id = os.environ.get("P0_WITHDRAW_ID", "")
            if not args.withdraw_id:
                raise SystemExit(f"{args.operation} requires --withdraw-id or P0_WITHDRAW_ID")
        if args.operation == "turnover-clear" and not args.member_uid:
            args.member_uid = os.environ.get("P0_MEMBER_UID", "")
            if not args.member_uid:
                raise SystemExit("turnover-clear requires --member-uid or P0_MEMBER_UID")
        self.apply_operation_client_lane(args)


