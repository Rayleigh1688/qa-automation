"""FILBET registration operations on one ControlledFlow instance."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from .constants import DEFAULT_REGISTER_PHONE_START
ROOT_DIR = Path(__file__).resolve().parents[2]


class RegistrationOperations:
    def register_new_user(self, args: argparse.Namespace) -> list[dict[str, object]]:
        phone = args.register_phone or os.environ.get("REGISTER_PHONE", "")
        if not phone:
            raise SystemExit("REGISTER_PHONE or --register-phone is required; use an allocated 090XXXXXXXX KYC test account")
        password = os.environ.get("REGISTER_PASSWORD", "")
        if not password:
            raise SystemExit("REGISTER_PASSWORD is required for registration")
        code = os.environ.get("REGISTER_OTP") or os.environ.get("CLIENT_OTP")
        otp_source = os.environ.get(
            "REGISTER_OTP_SOURCE",
            os.environ.get("CLIENT_OTP_SOURCE", "fixed"),
        ).strip().lower()
        if not code and otp_source != "admin_sms":
            raise SystemExit(
                "REGISTER_OTP/CLIENT_OTP or REGISTER_OTP_SOURCE=admin_sms is required for registration"
            )

        sms_body = {
            "country_code": os.environ.get("REGISTER_COUNTRY_CODE", os.environ.get("CLIENT_COUNTRY_CODE", "63")),
            "phone": phone,
            "reason": os.environ.get("REGISTER_SMS_REASON", ""),
        }
        sms_result = self.smoke.request_once(
            self.row("POST", "{{api_url}}/member/sms"),
            args.timeout,
            args.insecure,
            sms_body,
            args.body_format,
        )
        otp_id = ""
        data = self.data_of(sms_result)
        if isinstance(data, dict):
            otp_id = str(data.get("id") or data.get("otp_id") or "")

        records = [self.result_record("register_sms", sms_result)]
        if not otp_id:
            records.append({
                "name": "register",
                "business_status": False,
                "skipped": True,
                "reason": "missing otp_id",
                "phone_masked": self.masked_phone(phone),
            })
            return records

        if not code and otp_source == "admin_sms":
            code = self.smoke.admin_sms_otp(args, otp_id)
        if not code:
            records.append({
                "name": "register",
                "business_status": False,
                "skipped": True,
                "reason": "registration OTP lookup failed",
                "phone": phone,
            })
            return records

        register_body = {
            "otp_id": otp_id,
            "code": code,
            "password": password,
            "invite_code": os.environ.get("REGISTER_INVITE_CODE", ""),
            "i": os.environ.get("REGISTER_I", ""),
        }
        register_result = self.smoke.request_once(
            self.row("POST", "{{api_url}}/member/register"),
            args.timeout,
            args.insecure,
            register_body,
            args.body_format,
        )
        register_data = self.data_of(register_result)
        register_token = str(register_data.get("token") or "") if isinstance(register_data, dict) else ""
        if register_token:
            os.environ["API_TOKEN"] = register_token
            os.environ["CLIENT_PHONE"] = phone
            os.environ["CLIENT_PASSWORD"] = password
            args.client_phone = phone
        register_record = self.result_record("register", register_result)
        register_record["phone_masked"] = self.masked_phone(phone)
        records.append(register_record)
        return records


    def masked_phone(self, phone: str) -> str:
        return "*" * max(len(phone) - 4, 0) + phone[-4:]


    def phone_cursor_path(self, env_path: str) -> Path:
        name = Path(env_path).name.lower()
        if name.startswith(".env."):
            name = name[5:]
        elif name.startswith("env."):
            name = name[4:]
        safe_name = "".join(character if character.isalnum() else "-" for character in name).strip("-")
        return self.PHONE_CURSOR_DIR / f"register-phone-{safe_name or 'test'}.json"


    def load_phone_cursor(self, path: Path) -> str:
        if not path.is_file():
            return ""
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise SystemExit(f"registration phone cursor is invalid: {path}") from error
        value = payload.get("next_start") if isinstance(payload, dict) else ""
        if not isinstance(value, str) or not value.isdigit():
            raise SystemExit(f"registration phone cursor has no numeric next_start: {path}")
        return value


    def save_phone_cursor(self, path: Path, phone: str, env_path: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"environment_file": Path(env_path).name, "next_start": phone},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        path.chmod(0o600)


    def admin_member_exists(self, args: argparse.Namespace, phone: str) -> bool:
        result = self.smoke.request_once(
            self.row("POST", "{{admin_url}}/admin/member/list", "{{admin_url}}"),
            args.timeout,
            args.insecure,
            {"page": 1, "page_size": 10, "phone": phone},
            args.body_format,
        )
        if not self.business_ok(result):
            raise SystemExit("admin member lookup returned a business failure")
        data = self.data_of(result)
        rows = data.get("d") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            raise SystemExit("admin member lookup data.d is not a list")
        return any(
            isinstance(item, dict) and str(item.get("phone") or "") == phone
            for item in rows
        )


    def allocate_registration_phone(self, args: argparse.Namespace) -> tuple[str, dict[str, object]]:
        known_phone = os.environ.get("CLIENT_PHONE") or os.environ.get("WRITE_CLIENT_PHONE", "")
        if not known_phone:
            raise SystemExit("CLIENT_PHONE or WRITE_CLIENT_PHONE is required to verify admin phone filtering")
        if not self.admin_member_exists(args, known_phone):
            raise SystemExit("admin phone filter could not locate the configured known member")

        cursor_path = self.phone_cursor_path(args.env)
        start = (
            args.register_phone
            or os.environ.get("REGISTER_PHONE", "")
            or os.environ.get("PROVISION_PHONE_START", "")
            or self.load_phone_cursor(cursor_path)
            or DEFAULT_REGISTER_PHONE_START
        )
        if not start.isdigit():
            raise SystemExit("registration phone start must be numeric")
        width = len(start)
        for offset in range(args.register_scan_limit):
            candidate = str(int(start) + offset).zfill(width)
            if not self.admin_member_exists(args, candidate):
                self.save_phone_cursor(cursor_path, candidate, args.env)
                try:
                    cursor_display = str(cursor_path.relative_to(ROOT_DIR))
                except ValueError:
                    cursor_display = str(cursor_path)
                return candidate, {
                    "name": "register_phone_allocate",
                    "business_status": True,
                    "phone_masked": self.masked_phone(candidate),
                    "checked_candidates": offset + 1,
                    "cursor_file": cursor_display,
                }
        raise SystemExit(f"no unregistered phone found within {args.register_scan_limit} candidates")


