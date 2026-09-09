"""FILBET common operations on one ControlledFlow instance."""
from __future__ import annotations
import argparse
import json
import os
import time
from urllib.parse import parse_qs, urlparse


class CommonOperations:
    def row(self, method: str, clean_url: str, base_var: str = "{{api_url}}") -> dict[str, str]:
        return {
            "priority": "CONTROLLED",
            "method": method,
            "clean_url": clean_url,
            "suggested_base_var": base_var,
        }


    def business_ok(self, result: dict[str, object]) -> bool:
        body = result.get("decoded_body")
        return isinstance(body, dict) and body.get("status") is True


    def approval_code(self, args: argparse.Namespace) -> str:
        explicit = args.approval_code
        if explicit:
            if explicit == self.LAST_APPROVAL_CODE:
                raise SystemExit("the explicit approval code cannot be reused for another approval action")
            self.LAST_APPROVAL_CODE = explicit
            return explicit
        secret = os.environ.get("ADMIN_APPROVAL_TOTP_SECRET", "")
        algorithm = os.environ.get("ADMIN_APPROVAL_TOTP_ALGORITHM", "SHA1")
        if secret:
            seconds_remaining = 30 - (int(time.time()) % 30)
            if seconds_remaining <= 3:
                time.sleep(seconds_remaining + 1)
            code = self.current_totp(secret, algorithm=algorithm)
            if code == self.LAST_APPROVAL_CODE:
                seconds_remaining = 30 - (int(time.time()) % 30)
                time.sleep(seconds_remaining + 1)
                code = self.current_totp(secret, algorithm=algorithm)
            self.LAST_APPROVAL_CODE = code
            return code
        fallback = os.environ.get("ADMIN_APPROVAL_CODE", "")
        if fallback:
            if fallback == self.LAST_APPROVAL_CODE:
                raise SystemExit(
                    "ADMIN_APPROVAL_CODE is a single-use fallback and cannot be reused; configure ADMIN_APPROVAL_TOTP_SECRET"
                )
            self.LAST_APPROVAL_CODE = fallback
        return fallback


    def add_approval_code(self, body: dict[str, object], args: argparse.Namespace) -> dict[str, object]:
        code = self.approval_code(args)
        if code:
            value = int(code) if str(code).isdigit() else code
            body["google_code"] = value
        return body


    def now_window(self, days: int = 2) -> tuple[int, int]:
        end_time = int(time.time())
        return end_time - days * 86400, end_time + 300


    def data_of(self, result: dict[str, object]) -> object:
        body = result.get("decoded_body")
        if isinstance(body, dict):
            return body.get("data")
        return None


    def list_rows(self, data: object) -> list[dict[str, object]]:
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            rows = data.get("d") or data.get("data") or data.get("list")
            if isinstance(rows, list):
                return [item for item in rows if isinstance(item, dict)]
        return []


    def result_record(self, name: str, result: dict[str, object]) -> dict[str, object]:
        data = self.redact_payload(self.data_of(result))
        decoded = self.redact_payload(result.get("decoded_body"))
        return {
            "name": name,
            "url": result.get("url"),
            "http_status": result.get("status"),
            "business_status": (result.get("decoded_body") or {}).get("status")
            if isinstance(result.get("decoded_body"), dict)
            else None,
            "data": data,
            "elapsed_ms": result.get("elapsed_ms"),
            "body_sample": json.dumps(decoded, ensure_ascii=False)[:2000] if decoded is not None else "",
        }


    def redact_payload(self, value: object, key: str = "") -> object:
        sensitive_keys = {"token", "password", "code", "google_code", "otp", "pay_url"}
        if key.lower() in sensitive_keys:
            return "<redacted>"
        if isinstance(value, dict):
            return {str(item_key): self.redact_payload(item_value, str(item_key)) for item_key, item_value in value.items()}
        if isinstance(value, list):
            return [self.redact_payload(item) for item in value]
        return value


    def extract_deposit_external_order_id(self, data: object) -> str:
        if not isinstance(data, dict):
            return ""
        explicit = data.get("external_order_id")
        if explicit:
            return str(explicit)
        pay_url = str(data.get("pay_url") or "")
        if not pay_url:
            return ""
        query = parse_qs(urlparse(pay_url).query)
        return (query.get("checkoutId") or query.get("external_order_id") or [""])[0]


