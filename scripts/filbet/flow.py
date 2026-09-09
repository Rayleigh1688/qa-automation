"""FILBET flow operations on one ControlledFlow instance."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from filbet.reporting import report_verdict, write_html_report
from .constants import OPERATION_FLAGS


class FlowOperations:
    def finish(self, args: argparse.Namespace, records: list[dict[str, object]]) -> None:
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        report_name = args.operation or getattr(args, "flow_name", "")
        if report_name:
            for item in records:
                item["operation"] = report_name
        output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {output.resolve()}")
        if report_name:
            report_items: list[dict[str, str]] = []
            for index, item in enumerate(records, 1):
                business_status = item.get("business_status")
                if business_status is True:
                    status = "PASS"
                elif item.get("skipped"):
                    status = "SKIPPED"
                else:
                    status = "FAIL"
                raw_url = str(item.get("url") or "")
                parsed_url = urlparse(raw_url)
                safe_url = (
                    f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                    if parsed_url.scheme and parsed_url.netloc
                    else parsed_url.path
                )
                report_items.append({
                    "group": report_name,
                    "id": f"{report_name}-{index:02d}",
                    "name": str(item.get("name") or "unnamed"),
                    "kind": "API",
                    "status": status,
                    "target": safe_url,
                    "expected": "HTTP 请求完成且业务状态为 true",
                    "actual": (
                        f"HTTP={item.get('http_status', '—')}, "
                        f"business={business_status if business_status is not None else '—'}"
                    ),
                    "duration": f"{item.get('elapsed_ms')} ms" if item.get("elapsed_ms") is not None else "",
                    "detail": str(item.get("reason") or ""),
                })
            verdict, detail = report_verdict(report_items)
            html_output = output.with_suffix(".html")
            write_html_report(
                title=f"P0 API 操作报告 · {report_name}",
                scope="UAT" if ".uat" in Path(args.env).name.lower() else "FAT",
                report_kind="API 独立操作",
                verdict=verdict,
                verdict_detail=detail,
                items=report_items,
                output=html_output,
                metadata=[("原始结果", str(output))],
            )
            self.OPERATION_REPORT_WRITTEN = True
            print(f"HTML report: {html_output.resolve()}")
        for item in records:
            status = item.get("business_status")
            raw_url = str(item.get("url") or "")
            parsed_url = urlparse(raw_url)
            safe_url = (
                f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                if parsed_url.scheme and parsed_url.netloc
                else parsed_url.path
            )
            print(f"{item.get('name')} http={item.get('http_status')} business={status} url={safe_url}")
        failed_names = [
            str(item.get("name") or "unnamed")
            for item in records
            if item.get("business_status") is False
        ]
        if failed_names:
            raise SystemExit("controlled flow business failure: " + ", ".join(failed_names))


    def build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()
        parser.add_argument("--env", default=os.environ.get("ENV_FILE", ".env.fat"))
        parser.add_argument("--timeout", type=float, default=10)
        parser.add_argument("--insecure", action="store_true")
        parser.add_argument("--body-format", choices=["json", "cbor"], default="cbor")
        parser.add_argument("--out", default="")
        parser.add_argument("--flow-name", default="")
        parser.add_argument(
            "--operation",
            choices=sorted(OPERATION_FLAGS),
            default="",
            help="Run one independent P0 API operation with fresh authentication",
        )
        parser.add_argument("--register", action="store_true")
        parser.add_argument("--submit-kyc", action="store_true")
        parser.add_argument("--approve-kyc", action="store_true")
        parser.add_argument("--complete-kyc", action="store_true", help="Submit when ready, approve pending record, then verify client status")
        parser.add_argument("--deposit", action="store_true")
        parser.add_argument("--check-client-deposit-list", action="store_true")
        parser.add_argument("--check-admin-deposit-list", action="store_true")
        parser.add_argument("--approve-deposit", action="store_true")
        parser.add_argument("--withdraw", action="store_true")
        parser.add_argument("--prepare-withdraw-account", action="store_true")
        parser.add_argument("--approve-withdraw", action="store_true")
        parser.add_argument("--check-client-withdraw-list", action="store_true")
        parser.add_argument("--check-admin-withdraw-list", action="store_true")
        parser.add_argument("--clear-turnover", action="store_true")
        parser.add_argument("--main-positive-flow", action="store_true")
        parser.add_argument("--client-phone", default="")
        parser.add_argument("--client-otp", default="")
        parser.add_argument("--use-register-phone", action="store_true")
        parser.add_argument("--register-phone", default="")
        parser.add_argument("--register-scan-limit", type=int, default=200)
        parser.add_argument("--kyc-image", default="21000000008072.webp")
        parser.add_argument("--kyc-first-name", default="Codex")
        parser.add_argument("--kyc-middle-name", default="")
        parser.add_argument("--kyc-last-name", default="001")
        parser.add_argument("--kyc-birthday", default="1993-08-31")
        parser.add_argument("--kyc-gender", choices=["male", "female"], default="male")
        parser.add_argument("--kyc-nationality", default="Philippines")
        parser.add_argument("--kyc-place-of-birth", default="Manila")
        parser.add_argument("--kyc-current-address", default="Manila")
        parser.add_argument("--kyc-permanent-address", default="Manila")
        parser.add_argument("--kyc-nearest-branch", default="2040 Taft Ave, Pasay, Metro Mani")
        parser.add_argument("--kyc-nature-of-work", default="Employed – Permanent/Contractual")
        parser.add_argument("--kyc-source-of-income", default="Employment Income")
        parser.add_argument("--kyc-id-type", default="COUNTRY_ID")
        parser.add_argument("--kyc-id-number", default="")
        parser.add_argument("--kyc-uid", default="")
        parser.add_argument("--kyc-status-attempts", type=int, default=10)
        parser.add_argument("--kyc-status-interval", type=float, default=1)
        parser.add_argument("--member-uid", default="")
        parser.add_argument("--deposit-pid", default="")
        parser.add_argument("--deposit-amount", default="")
        parser.add_argument("--deposit-product-id", default="")
        parser.add_argument("--deposit-id", default="")
        parser.add_argument("--deposit-cashback-flag", choices=["0", "1"], default="0")
        parser.add_argument("--deposit-rotation-flag", choices=["0", "1"], default="0")
        parser.add_argument("--deposit-external-order-id", default="")
        parser.add_argument("--deposit-status", default="")
        parser.add_argument("--deposit-lookup-attempts", type=int, default=6)
        parser.add_argument("--deposit-lookup-interval", type=float, default=1)
        parser.add_argument("--wallet-settlement-attempts", type=int, default=20)
        parser.add_argument("--wallet-settlement-interval", type=float, default=1)
        parser.add_argument("--withdraw-account-id", default="")
        parser.add_argument("--wallet-password", default="")
        parser.add_argument("--maya-account", default="")
        parser.add_argument("--maya-pid", default="")
        parser.add_argument("--maya-first-name", default="Codex")
        parser.add_argument("--maya-middle-name", default="")
        parser.add_argument("--maya-last-name", default="001")
        parser.add_argument("--withdraw-id", default="")
        parser.add_argument("--withdraw-amount", default="")
        parser.add_argument("--withdraw-client-phone", default="")
        parser.add_argument("--withdraw-client-otp", default="")
        parser.add_argument("--withdraw-status", default="")
        parser.add_argument("--withdraw-lookup-attempts", type=int, default=15)
        parser.add_argument("--withdraw-lookup-interval", type=float, default=1)
        parser.add_argument("--withdraw-mark-success", action="store_true")
        parser.add_argument("--withdraw-external-order-id", default="")
        parser.add_argument("--approval-desc", default="p0 automation")
        parser.add_argument("--approval-code", default="")
        parser.add_argument("--turnover-clear-remark", default="p0 api no-bet flow")
        parser.add_argument("--turnover-clear-attempts", type=int, default=10)
        parser.add_argument("--turnover-clear-interval", type=float, default=1)
        parser.add_argument("--turnover-discovery-attempts", type=int, default=30)
        parser.add_argument("--turnover-discovery-interval", type=float, default=1)
        return parser


    def main(self) -> None:
        args = self.build_parser().parse_args()
        if not args.out:
            args.out = (
                f"api/results/operations/{args.operation}.json"
                if args.operation
                else "api/results/controlled-write-result.json"
            )
        self.ACTIVE_ARGS = args

        self.smoke.load_env_file(Path(args.env))
        self.configure_operation(args)
        if args.use_register_phone or not args.operation:
            self.apply_primary_client_override(args)
        os.environ.pop("API_TOKEN", None)
        os.environ.pop("ADMIN_TOKEN", None)
        records: list[dict[str, object]] = []
        self.ACTIVE_RECORDS = records

        if args.main_positive_flow:
            args.register = True
            args.deposit = True
            args.approve_deposit = True
            # Stop at the deposit checkpoint. A real game bet and asynchronous
            # turnover reconciliation must happen before any withdrawal attempt.

        if args.register:
            if not (args.register_phone or os.environ.get("REGISTER_PHONE", "")):
                records.extend(self.admin_login(args))
                allocated_phone, allocation_record = self.allocate_registration_phone(args)
                args.register_phone = allocated_phone
                records.append(allocation_record)
            register_records = self.register_new_user(args)
            records.extend(register_records)
            if any(item.get("business_status") is not True for item in register_records):
                self.finish(args, records)
                return

        if args.complete_kyc:
            kyc_start = len(records)
            records.extend(self.client_login(args))
            records.append({
                "name": "register",
                "business_status": True,
                "skipped": True,
                "reason": "allocated KYC pool account already exists and authenticated",
            })
            current_detail = self.smoke.request_once(
                self.row("GET", "{{api_url}}/member/kyc/detail"), args.timeout, args.insecure
            )
            current_profile = self.data_of(current_detail)
            current_status = int(current_profile.get("kyc_status") or 0) if isinstance(current_profile, dict) else -1
            if current_status == 0:
                records.extend(self.submit_kyc(args))
                submitted = records[-1].get("data") if records else None
                current_status = int(submitted.get("kyc_status") or 0) if isinstance(submitted, dict) else 0
            else:
                records.append(self.result_record("kyc_detail_existing", current_detail))
                if current_status != 5:
                    records.append({
                        "name": "kyc_submit",
                        "business_status": True,
                        "skipped": True,
                        "reason": f"existing submitted KYC status={current_status}",
                        "data": current_profile,
                    })
            kyc_uid = self.resolve_kyc_uid(args, current_profile)
            if not kyc_uid:
                raise SystemExit("KYC uid is required for controlled approval")
            args.member_uid = kyc_uid
            if current_status == 5:
                existing = self.result_record("kyc_detail_after_approval", current_detail)
                existing["business_status"] = True
                existing["expected_kyc_status"] = 5
                existing["actual_kyc_status"] = 5
                records.extend([
                    {"name": "kyc_submit", "business_status": True, "skipped": True, "reason": "KYC pool account is already approved"},
                    {"name": "admin_kyc_approve", "business_status": True, "skipped": True, "reason": "KYC already approved"},
                    existing,
                ])
            else:
                records.extend(self.admin_login(args))
                records.extend(self.approve_kyc(args, kyc_uid))
            if any(item.get("business_status") is False for item in records[kyc_start:]):
                self.finish(args, records)
                return

        if args.submit_kyc and not args.complete_kyc:
            records.extend(self.client_login(args))
            records.extend(self.submit_kyc(args))

        if args.approve_kyc and not args.complete_kyc:
            if not args.submit_kyc:
                records.extend(self.client_login(args))
            kyc_uid = self.resolve_kyc_uid(args)
            if not kyc_uid:
                detail = self.smoke.request_once(
                    self.row("GET", "{{api_url}}/member/kyc/detail"), args.timeout, args.insecure
                )
                profile = self.data_of(detail)
                kyc_uid = self.resolve_kyc_uid(args, profile)
            if not kyc_uid:
                raise SystemExit("KYC uid is required for controlled approval")
            args.member_uid = kyc_uid
            records.extend(self.admin_login(args))
            records.extend(self.approve_kyc(args, kyc_uid))

        current_phone = os.environ.get("CLIENT_PHONE", "")
        withdraw_phone = (
            current_phone
            if args.use_register_phone
            else args.withdraw_client_phone or os.environ.get("WITHDRAW_CLIENT_PHONE", "")
        )
        separate_withdraw_client = bool(
            args.withdraw
            and withdraw_phone
            and "".join(filter(str.isdigit, withdraw_phone)) != "".join(filter(str.isdigit, current_phone))
        )

        if (
            args.deposit
            or args.clear_turnover
            or args.prepare_withdraw_account
            or (args.withdraw and not separate_withdraw_client)
        ):
            records.extend(self.client_login(args))
            if args.deposit or args.clear_turnover or args.withdraw:
                records.append(self.query_wallet(args, "wallet_before"))
        elif args.check_client_deposit_list or args.check_client_withdraw_list:
            records.extend(self.client_login(args))
        if (
            args.approve_deposit
            or args.check_admin_deposit_list
            or args.clear_turnover
            or args.approve_withdraw
            or args.check_admin_withdraw_list
        ):
            records.extend(self.admin_login(args))
        if args.deposit:
            if not self.run_deposit_stage(args, records):
                self.finish(args, records)
                return
            if args.approve_deposit:
                wallet_before = next(
                    (item for item in records if item.get("name") == "wallet_before"),
                    {},
                )
                wallet_after_deposit = self.wait_for_deposit_credit(
                    args,
                    wallet_before,
                    args.deposit_amount,
                )
                records.append(wallet_after_deposit)
                if wallet_after_deposit.get("business_status") is not True:
                    self.finish(args, records)
                    return
        elif args.approve_deposit and args.deposit_id:
            if args.deposit_external_order_id:
                records.extend(
                    self.approve_deposit(
                        args,
                        None,
                        args.deposit_id,
                        args.deposit_external_order_id,
                    )
                )
            else:
                list_record, order = self.find_deposit_order(args, args.deposit_id)
                records.append(list_record)
                if list_record.get("business_status") is True:
                    records.extend(self.approve_deposit(args, order, args.deposit_id, ""))
        elif args.check_admin_deposit_list:
            list_record, _ = self.find_deposit_order(args, args.deposit_id)
            records.append(list_record)
        if args.clear_turnover:
            uid = args.member_uid
            if not uid and os.environ.get("API_TOKEN"):
                detail = self.smoke.request_once(
                    self.row("GET", "{{api_url}}/member/detail"), args.timeout, args.insecure
                )
                records.append(self.result_record("member_detail_for_turnover", detail))
                profile = self.data_of(detail)
                uid = str(profile.get("uid") or "") if isinstance(profile, dict) else ""
            if not uid:
                raise SystemExit("member uid is required before clearing turnover")
            args.member_uid = uid
            wallet_checkpoint = next(
                (
                    item
                    for item in reversed(records)
                    if item.get("name") in {"wallet_after_deposit", "wallet_before"}
                ),
                {},
            )
            wallet_data = wallet_checkpoint.get("data")
            expected_locked = (
                self.decimal_value(wallet_data.get("locked"))
                if isinstance(wallet_data, dict)
                else None
            )
            turnover_records = self.run_turnover_clear(args, uid, expected_locked)
            records.extend(turnover_records)
            if any(item.get("business_status") is not True for item in turnover_records):
                self.finish(args, records)
                return
        if args.prepare_withdraw_account:
            prepare_records = self.prepare_withdraw_account(args)
            records.extend(prepare_records)
            if any(item.get("business_status") is not True for item in prepare_records):
                self.finish(args, records)
                return
        created_withdraw_id = ""
        if args.withdraw and separate_withdraw_client:
            previous_phone, previous_password, previous_otp, previous_token = self.use_withdraw_client(args)
            try:
                records.extend(self.relabel(self.client_login(args), "withdraw"))
                records.append(self.query_wallet(args, "withdraw_wallet_before"))
                withdrawable_record = self.wait_for_withdrawable_funds(args)
                records.append(withdrawable_record)
                if withdrawable_record.get("business_status") is not True:
                    self.finish(args, records)
                    return
                withdraw_ok, withdraw_id = self.run_withdraw_stage(args, records)
                if not withdraw_ok:
                    self.finish(args, records)
                    return
                created_withdraw_id = withdraw_id
                if args.check_admin_withdraw_list:
                    records.extend(self.check_admin_withdraw_list(args, withdraw_id))
                if args.approve_withdraw:
                    list_record, order = self.find_withdraw_order(args, withdraw_id)
                    records.append(list_record)
                    records.extend(self.approve_withdraw(args, order))
                records.append(self.query_wallet(args, "withdraw_wallet_after"))
            finally:
                self.restore_client(previous_phone, previous_password, previous_otp, previous_token)
        elif args.withdraw:
            withdrawable_record = self.wait_for_withdrawable_funds(args)
            records.append(withdrawable_record)
            if withdrawable_record.get("business_status") is not True:
                self.finish(args, records)
                return
            withdraw_ok, withdraw_id = self.run_withdraw_stage(args, records)
            if not withdraw_ok:
                self.finish(args, records)
                return
            created_withdraw_id = withdraw_id
            if args.check_admin_withdraw_list:
                records.extend(self.check_admin_withdraw_list(args, withdraw_id))
            if args.approve_withdraw:
                list_record, order = self.find_withdraw_order(args, withdraw_id)
                records.append(list_record)
                records.extend(self.approve_withdraw(args, order))
        elif args.approve_withdraw and args.withdraw_id:
            list_record, order = self.find_withdraw_order(args, args.withdraw_id)
            records.append(list_record)
            if list_record.get("business_status") is True:
                records.extend(self.approve_withdraw(args, order))
        elif args.check_admin_withdraw_list:
            records.extend(self.check_admin_withdraw_list(args, args.withdraw_id))
        if args.check_client_withdraw_list:
            records.extend(self.check_client_withdraw_list(args, args.withdraw_id or created_withdraw_id))
        if args.check_client_deposit_list:
            records.extend(self.check_client_deposit_list(args, args.deposit_id))
        if args.deposit or (args.withdraw and not separate_withdraw_client):
            records.append(self.query_wallet(args, "wallet_after"))

        self.finish(args, records)


