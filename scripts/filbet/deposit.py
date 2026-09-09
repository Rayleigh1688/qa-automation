"""FILBET deposit operations on one ControlledFlow instance."""
from __future__ import annotations
import argparse
import time
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode


class DepositOperations:
    def decimal_value(self, value: object) -> Decimal | None:
        try:
            parsed = Decimal(str(value))
            return parsed if parsed.is_finite() else None
        except (InvalidOperation, TypeError, ValueError):
            return None


    def channel_amount_options(self, channel: dict[str, object]) -> list[Decimal]:
        raw_options = channel.get("amount_limit")
        if not isinstance(raw_options, list):
            return []
        options: list[Decimal] = []
        for raw in raw_options:
            if isinstance(raw, dict):
                raw = raw.get("amount", raw.get("value"))
            parsed = self.decimal_value(raw)
            if parsed is not None:
                options.append(parsed)
        return options


    def channel_accepts_amount(self, channel: dict[str, object], amount: str) -> bool:
        requested = self.decimal_value(amount)
        if requested is None or requested <= 0:
            return False
        minimum = self.decimal_value(channel.get("min_amount"))
        maximum = self.decimal_value(channel.get("max_amount"))
        if minimum is not None and requested < minimum:
            return False
        if maximum is not None and requested > maximum:
            return False
        return True


    def default_channel_amount(self, channel: dict[str, object]) -> str:
        options = self.channel_amount_options(channel)
        for option in options:
            if self.channel_accepts_amount(channel, str(option)):
                return str(option)
        return str(channel.get("min_amount") or "1")


    def choose_deposit_channel(self, args: argparse.Namespace) -> tuple[str, str]:
        channels_result = self.smoke.request_once(
            self.row("GET", "{{api_url}}/finance/channel/list?mode=1"),
            args.timeout,
            args.insecure,
        )
        channels = self.data_of(channels_result)
        if not isinstance(channels, list) or not channels:
            raise SystemExit("no deposit channels available")

        usable_channels = [item for item in channels if isinstance(item, dict) and item.get("id")]
        if args.deposit_pid:
            usable_channels = [item for item in usable_channels if str(item.get("id")) == args.deposit_pid]
            if not usable_channels:
                raise SystemExit(f"configured deposit channel is unavailable: pid={args.deposit_pid}")

        requested_amount = args.deposit_amount
        if requested_amount:
            usable_channels = [
                item for item in usable_channels if self.channel_accepts_amount(item, requested_amount)
            ]
            if not usable_channels:
                pid_context = f" for pid={args.deposit_pid}" if args.deposit_pid else ""
                raise SystemExit(
                    f"no deposit channel accepts amount={requested_amount}{pid_context}; "
                    "check min_amount and max_amount"
                )

        if not usable_channels:
            raise SystemExit("no usable deposit channels available")
        requested = self.decimal_value(requested_amount) if requested_amount else None
        channel = next(
            (
                item for item in usable_channels
                if requested is not None and requested in self.channel_amount_options(item)
            ),
            usable_channels[0],
        )
        amount = requested_amount or self.default_channel_amount(channel)
        if not self.channel_accepts_amount(channel, amount):
            raise SystemExit(f"deposit channel pid={channel['id']} has no valid amount tier")
        return str(channel["id"]), amount


    def run_deposit(self, args: argparse.Namespace) -> list[dict[str, object]]:
        pid, amount = self.choose_deposit_channel(args)
        query = (
            f"pid={pid}&amount={amount}&device=web&source=huawei"
            f"&cashback_flag={args.deposit_cashback_flag}&rotation_flag={args.deposit_rotation_flag}"
        )
        if args.deposit_product_id:
            query += f"&product_id={args.deposit_product_id}"
        deposit_result = self.smoke.request_once(
            self.row("GET", "{{api_url}}/finance/payment/deposit?" + query),
            args.timeout,
            args.insecure,
        )
        record = self.result_record("deposit_create", deposit_result)
        deposit_data = self.data_of(deposit_result)
        record["pid"] = pid
        record["amount"] = amount
        record["cashback_flag"] = args.deposit_cashback_flag
        record["rotation_flag"] = args.deposit_rotation_flag
        external_order_id = args.deposit_external_order_id or self.extract_deposit_external_order_id(deposit_data)
        if external_order_id:
            record["external_order_id"] = external_order_id
        return [record]


    def run_deposit_stage(self, args: argparse.Namespace, records: list[dict[str, object]]) -> bool:
        deposit_records = self.run_deposit(args)
        records.extend(deposit_records)
        if any(item.get("business_status") is not True for item in deposit_records):
            for item in deposit_records:
                if item.get("business_status") is not True:
                    item["business_status"] = False
            return False

        deposit_data = deposit_records[-1].get("data")
        deposit_id = str(deposit_data.get("id") or deposit_data.get("order_id") or "") if isinstance(deposit_data, dict) else ""
        deposit_external_order_id = str(deposit_records[-1].get("external_order_id") or "")
        if args.approve_deposit:
            client_records = self.check_client_deposit_list(args, deposit_id)
            records.extend(client_records)
            if any(item.get("business_status") is not True for item in client_records):
                return False
            matched_order = client_records[-1].get("matched_order")
            if isinstance(matched_order, dict):
                deposit_external_order_id = str(
                    matched_order.get("external_order_id")
                    or matched_order.get("merchant_order_id")
                    or deposit_external_order_id
                )
            if not deposit_id or not deposit_external_order_id:
                records.append({
                    "name": "deposit_identifiers",
                    "business_status": False,
                    "reason": "client deposit record is missing id or external_order_id",
                })
                return False
            approval_records = self.approve_deposit(
                args,
                None,
                deposit_id,
                deposit_external_order_id,
            )
            records.extend(approval_records)
            if any(item.get("business_status") is not True for item in approval_records):
                for item in approval_records:
                    if item.get("business_status") is not True:
                        item["business_status"] = False
                return False
        return True


    def check_client_deposit_list(self, args: argparse.Namespace, deposit_id: str) -> list[dict[str, object]]:
        identifiers = (
            "id",
            "order_id",
            "external_order_id",
            "merchant_order_id",
            "transaction_id",
        )
        attempts = max(1, int(getattr(args, "deposit_lookup_attempts", 1)))
        interval = max(0.0, float(getattr(args, "deposit_lookup_interval", 0)))
        result: dict[str, object] = {}
        matched = None
        for attempt in range(attempts):
            result = self.smoke.request_once(
                self.row("GET", "{{api_url}}/finance/deposit/list?page=1&page_size=50&time_flag=0"),
                args.timeout,
                args.insecure,
            )
            rows = self.list_rows(self.data_of(result))
            matched = next(
                (
                    item
                    for item in rows
                    if any(str(item.get(key) or "") == str(deposit_id) for key in identifiers)
                ),
                None,
            )
            if matched is not None or attempt + 1 >= attempts:
                break
            time.sleep(interval)
        record = self.result_record("client_deposit_list", result)
        record["matched_order"] = matched
        if matched is None:
            record["business_status"] = False
            record["reason"] = f"deposit order not found: id={deposit_id}"
        return [record]


    def find_deposit_order(self, args: argparse.Namespace, deposit_id: str = "") -> tuple[dict[str, object], dict[str, object] | None]:
        start_time, end_time = self.now_window()
        base_params: dict[str, object] = {
            "status": args.deposit_status or "PENDING",
            "start_time": start_time * 1000,
            "end_time": end_time * 1000,
            "page": 1,
            "page_size": 50,
        }
        attempts = max(1, int(getattr(args, "deposit_lookup_attempts", 1)))
        interval = max(0.0, float(getattr(args, "deposit_lookup_interval", 0)))
        result: dict[str, object] = {}
        target = None
        for attempt in range(attempts):
            params = dict(base_params)
            # Some FAT admin deployments accept only their internal id here,
            # while deposit-create returns the client order_id. Try the narrow
            # server filter first, then poll the recent pending page and match the
            # same identifier locally. Never fall back to an unrelated first row.
            if deposit_id and attempt == 0:
                params["id"] = deposit_id
            result = self.smoke.request_once(
                self.row("POST", "{{admin_url}}/admin/finance/deposit/risk/list", "{{admin_url}}"),
                args.timeout,
                args.insecure,
                params,
                args.body_format,
            )
            result["url"] = str(result.get("url") or "") + "?" + urlencode(params)
            rows = self.list_rows(self.data_of(result))
            if deposit_id:
                identifiers = (
                    "id",
                    "order_id",
                    "external_order_id",
                    "merchant_order_id",
                    "transaction_id",
                )
                target = next(
                    (
                        item
                        for item in rows
                        if any(str(item.get(key) or "") == str(deposit_id) for key in identifiers)
                    ),
                    None,
                )
            elif rows:
                target = rows[0]
            if target is not None or attempt + 1 >= attempts:
                break
            time.sleep(interval)
        record_name = "admin_deposit_risk_list"
        if deposit_id and target is None:
            # Online-channel orders may be visible in the general deposit ledger
            # before (or without) entering the risk-review queue.
            params = {
                "start_time": start_time * 1000,
                "end_time": end_time * 1000,
                "page": 1,
                "page_size": 100,
            }
            result = self.smoke.request_once(
                self.row("POST", "{{admin_url}}/admin/finance/deposit/list", "{{admin_url}}"),
                args.timeout,
                args.insecure,
                params,
                args.body_format,
            )
            result["url"] = str(result.get("url") or "") + "?" + urlencode(params)
            rows = self.list_rows(self.data_of(result))
            identifiers = (
                "id",
                "order_id",
                "external_order_id",
                "merchant_order_id",
                "transaction_id",
            )
            target = next(
                (
                    item
                    for item in rows
                    if any(str(item.get(key) or "") == str(deposit_id) for key in identifiers)
                ),
                None,
            )
            record_name = "admin_deposit_list"
        record = self.result_record(record_name, result)
        record["matched_order"] = target
        if deposit_id and target is None:
            record["business_status"] = False
            record["reason"] = f"deposit order not found: id={deposit_id}"
        return record, target


    def approve_deposit(self, 
        args: argparse.Namespace,
        deposit_order: dict[str, object] | None,
        fallback_id: str = "",
        fallback_external_order_id: str = "",
    ) -> list[dict[str, object]]:
        if not deposit_order and not fallback_id:
            return [{"name": "admin_deposit_manual_success", "skipped": True, "reason": "no pending deposit order found"}]
        deposit_id = str((deposit_order or {}).get("id") or fallback_id)
        if not deposit_id:
            return [{"name": "admin_deposit_manual_success", "skipped": True, "reason": "matched deposit has no id"}]
        external_order_id = str((deposit_order or {}).get("external_order_id") or args.deposit_external_order_id or fallback_external_order_id)
        body: dict[str, object] = {"id": deposit_id, "desc": args.approval_desc}
        if external_order_id:
            body["external_order_id"] = external_order_id
        body = self.add_approval_code(body, args)
        result = self.smoke.request_once(
            self.row("POST", "{{admin_url}}/admin/finance/deposit/manual/success", "{{admin_url}}"),
            args.timeout,
            args.insecure,
            body,
            args.body_format,
        )
        record = self.result_record("admin_deposit_manual_success", result)
        record["deposit_id"] = deposit_id
        if external_order_id:
            record["external_order_id"] = external_order_id
        return [record]


