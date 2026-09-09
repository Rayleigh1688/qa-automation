"""FILBET withdrawal operations on one ControlledFlow instance."""
from __future__ import annotations
import argparse
import time
from decimal import Decimal
from urllib.parse import urlencode
from .constants import DEFAULT_WITHDRAW_AMOUNT


class WithdrawalOperations:
    def choose_withdraw_account(self, args: argparse.Namespace) -> tuple[str, str, dict[str, object] | None]:
        if args.withdraw_account_id:
            return args.withdraw_account_id, args.withdraw_amount or DEFAULT_WITHDRAW_AMOUNT, None
        accounts_result = self.smoke.request_once(
            self.row("GET", "{{api_url}}/finance/account/list"),
            args.timeout,
            args.insecure,
        )
        accounts = self.data_of(accounts_result)
        if not isinstance(accounts, list) or not accounts:
            raise SystemExit("no withdraw accounts available")
        usable = [item for item in accounts if isinstance(item, dict) and item.get("id") and item.get("status") == 1]
        if not usable:
            raise SystemExit("no usable withdraw accounts available")
        account = sorted(usable, key=lambda item: float(item.get("min_amount") or 999999))[0]
        amount = args.withdraw_amount or DEFAULT_WITHDRAW_AMOUNT
        requested = self.decimal_value(amount)
        maximum = self.decimal_value(account.get("max_amount"))
        if requested is None or requested < Decimal(DEFAULT_WITHDRAW_AMOUNT):
            raise SystemExit(f"withdraw amount must be at least {DEFAULT_WITHDRAW_AMOUNT}")
        if maximum is not None and requested > maximum:
            raise SystemExit(f"withdraw amount exceeds selected account maximum={maximum}")
        return str(account["id"]), amount, account


    def run_withdraw(self, args: argparse.Namespace) -> list[dict[str, object]]:
        account_id, amount, account = self.choose_withdraw_account(args)
        withdraw_result = self.smoke.request_once(
            self.row("GET", f"{{{{api_url}}}}/finance/payment/withdraw?amount={amount}&account_id={account_id}"),
            args.timeout,
            args.insecure,
        )
        record = self.result_record("withdraw_create", withdraw_result)
        record["account_id"] = account_id
        record["amount"] = amount
        if account:
            record["selected_account"] = account
        return [record]


    def run_withdraw_stage(self, 
        args: argparse.Namespace,
        records: list[dict[str, object]],
    ) -> tuple[bool, str]:
        before_result, before_rows = self.fetch_client_withdraw_list(args)
        before_record = self.result_record("withdraw_list_before_create", before_result)
        records.append(before_record)
        if before_record.get("business_status") is not True:
            return False, ""
        existing_ids = {
            str(item.get("id") or item.get("order_no") or "")
            for item in before_rows
            if item.get("id") or item.get("order_no")
        }
        started_at_ms = int(time.time() * 1000)
        withdraw_records = self.run_withdraw(args)
        records.extend(withdraw_records)
        withdraw_data = withdraw_records[-1].get("data") if withdraw_records else None
        withdraw_id = (
            str(withdraw_data.get("id") or withdraw_data.get("order_no") or "")
            if isinstance(withdraw_data, dict)
            else ""
        )
        if withdraw_id and all(item.get("business_status") is True for item in withdraw_records):
            return True, withdraw_id

        create_record = withdraw_records[-1] if withdraw_records else {}
        amount = str(create_record.get("amount") or args.withdraw_amount or DEFAULT_WITHDRAW_AMOUNT)
        selected = create_record.get("selected_account")
        platform_id = (
            str(selected.get("payment_platform_id") or "")
            if isinstance(selected, dict)
            else ""
        )
        attempts = max(1, int(args.withdraw_lookup_attempts))
        interval = max(0.0, float(args.withdraw_lookup_interval))
        reconcile_record: dict[str, object] = {}
        matched = None
        for attempt in range(1, attempts + 1):
            lookup_result, lookup_rows = self.fetch_client_withdraw_list(args)
            candidates = []
            for item in lookup_rows:
                item_id = str(item.get("id") or item.get("order_no") or "")
                item_amount = self.decimal_value(item.get("amount"))
                created_at = int(item.get("created_at") or 0)
                same_platform = not platform_id or str(item.get("payment_platform_id") or "") == platform_id
                if (
                    item_id
                    and item_id not in existing_ids
                    and item_amount == self.decimal_value(amount)
                    and same_platform
                    and created_at >= started_at_ms - 2000
                ):
                    candidates.append(item)
            if candidates:
                matched = max(candidates, key=lambda item: int(item.get("created_at") or 0))
            reconcile_record = self.result_record("client_withdraw_async_reconcile", lookup_result)
            reconcile_record["matched_order"] = matched
            reconcile_record["poll_attempts"] = attempt
            if matched is not None or attempt == attempts:
                break
            time.sleep(interval)
        if matched is None:
            reconcile_record["business_status"] = False
            reconcile_record["reason"] = "withdraw response had no usable id and no new matching order appeared"
            records.append(reconcile_record)
            return False, ""

        withdraw_id = str(matched.get("id") or matched.get("order_no") or "")
        create_record["response_business_status"] = create_record.get("business_status")
        create_record["business_status"] = True
        create_record["async_reconciled"] = True
        create_record["reason"] = "synchronous response was inconclusive; a new matching order appeared asynchronously"
        reconcile_record["business_status"] = True
        reconcile_record["withdraw_id"] = withdraw_id
        records.append(reconcile_record)
        return True, withdraw_id


    def fetch_client_withdraw_list(self, 
        args: argparse.Namespace,
    ) -> tuple[dict[str, object], list[dict[str, object]]]:
        result = self.smoke.request_once(
            self.row("GET", "{{api_url}}/finance/withdraw/list?time_flag=0&page=1&page_size=50"),
            args.timeout,
            args.insecure,
        )
        return result, self.list_rows(self.data_of(result))


    def check_client_withdraw_list(self, args: argparse.Namespace, withdraw_id: str = "") -> list[dict[str, object]]:
        result, rows = self.fetch_client_withdraw_list(args)
        record = self.result_record("client_withdraw_list", result)
        matched = next((item for item in rows if str(item.get("id") or item.get("order_no") or "") == withdraw_id), None) if withdraw_id else (rows[0] if rows else None)
        record["matched_order"] = matched
        if withdraw_id and matched is None:
            record["business_status"] = False
            record["reason"] = f"withdraw order not found: id={withdraw_id}"
        return [record]


    def find_withdraw_order(self, args: argparse.Namespace, withdraw_id: str = "") -> tuple[dict[str, object], dict[str, object] | None]:
        start_time, end_time = self.now_window()
        params = {
            "status": args.withdraw_status or "under_review",
            "start_time": start_time * 1000,
            "end_time": end_time * 1000,
            "page": 1,
            "page_size": 10,
        }
        if withdraw_id:
            params["id"] = withdraw_id
        def request_list(body: dict[str, object]) -> dict[str, object]:
            response = self.smoke.request_once(
                self.row("POST", "{{admin_url}}/admin/finance/withdraw/risk/audit/list", "{{admin_url}}"),
                args.timeout,
                args.insecure,
                body,
                args.body_format,
            )
            response["url"] = response.get("url", "") + "?" + urlencode(body)
            return response

        result = request_list(params)
        rows = self.list_rows(self.data_of(result))
        if withdraw_id and not rows:
            # The FAT endpoint currently returns an empty page when id and time
            # filters are combined. Retry the same status page without those
            # filters, then match the controlled order id locally.
            result = request_list({
                "status": args.withdraw_status or "under_review",
                "page": 1,
                "page_size": 10,
            })
            rows = self.list_rows(self.data_of(result))
        target = None
        if withdraw_id:
            target = next((item for item in rows if str(item.get("id")) == str(withdraw_id)), None)
        elif rows:
            target = rows[0]
        record_name = "admin_withdraw_risk_audit_list"
        if withdraw_id and target is None:
            general_params = {
                "start_time": start_time * 1000,
                "end_time": end_time * 1000,
                "page": 1,
                "page_size": 100,
            }
            result = self.smoke.request_once(
                self.row("POST", "{{admin_url}}/admin/finance/withdraw/list", "{{admin_url}}"),
                args.timeout,
                args.insecure,
                general_params,
                args.body_format,
            )
            result["url"] = result.get("url", "") + "?" + urlencode(general_params)
            rows = self.list_rows(self.data_of(result))
            target = next((item for item in rows if str(item.get("id")) == str(withdraw_id)), None)
            record_name = "admin_withdraw_list"
        record = self.result_record(record_name, result)
        record["matched_order"] = target
        if withdraw_id and target is None:
            record["business_status"] = False
            record["reason"] = f"withdraw order not found: id={withdraw_id}"
        return record, target


    def check_admin_withdraw_list(self, args: argparse.Namespace, withdraw_id: str = "") -> list[dict[str, object]]:
        list_record, _ = self.find_withdraw_order(args, withdraw_id)
        return [list_record]


    def approve_withdraw(self, args: argparse.Namespace, withdraw_order: dict[str, object] | None) -> list[dict[str, object]]:
        if not withdraw_order:
            return [{"name": "admin_withdraw_agree", "skipped": True, "reason": "no under_review withdraw order found"}]
        withdraw_id = str(withdraw_order.get("id") or "")
        if not withdraw_id:
            return [{"name": "admin_withdraw_agree", "skipped": True, "reason": "matched withdraw has no id"}]
        status = str(withdraw_order.get("status") or "").strip().lower()
        if status and status != "under_review":
            return [{
                "name": "admin_withdraw_agree",
                "business_status": True,
                "skipped": True,
                "withdraw_id": withdraw_id,
                "reason": f"withdraw order already progressed to status={status}",
            }]
        body = self.add_approval_code({"id": withdraw_id, "desc": args.approval_desc}, args)
        agree_result = self.smoke.request_once(
            self.row("POST", "{{admin_url}}/admin/finance/withdraw/agree", "{{admin_url}}"),
            args.timeout,
            args.insecure,
            body,
            args.body_format,
        )
        records = [self.result_record("admin_withdraw_agree", agree_result)]
        records[0]["withdraw_id"] = withdraw_id
        if args.withdraw_mark_success:
            if not self.business_ok(agree_result):
                records.append({
                    "name": "admin_withdraw_success",
                    "skipped": True,
                    "reason": "withdraw agree failed; success transition is not allowed",
                    "withdraw_id": withdraw_id,
                })
                return records
            external_order_id = args.withdraw_external_order_id or f"p0-automation-{withdraw_id}"
            success_result = self.smoke.request_once(
                self.row("POST", "{{admin_url}}/admin/finance/withdraw/success", "{{admin_url}}"),
                args.timeout,
                args.insecure,
                {
                    **body,
                    "external_order_id": external_order_id,
                },
                args.body_format,
            )
            success_record = self.result_record("admin_withdraw_success", success_result)
            success_record["withdraw_id"] = withdraw_id
            records.append(success_record)
        return records


