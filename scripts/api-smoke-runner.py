#!/usr/bin/env python3
"""Run a P0 API smoke set from api/p0/test-cases.csv."""

from __future__ import annotations

import argparse
import csv
import json
import os
import ssl
import struct
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


VAR_DEFAULTS = {
    "{{api_url}}": "https://client-fat.filbet2025.com",
    "{{admin_url}}": "https://admin-fat.filbet2025.com",
    "{{agency_url}}": "",
}


ENV_NAMES = {
    "{{api_url}}": "API_URL",
    "{{admin_url}}": "ADMIN_URL",
    "{{agency_url}}": "AGENCY_URL",
}


class CborDecodeError(ValueError):
    pass


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def cbor_encode(value: object) -> bytes:
    if value is None:
        return b"\xf6"
    if value is False:
        return b"\xf4"
    if value is True:
        return b"\xf5"
    if isinstance(value, int):
        return _cbor_encode_type_value(0 if value >= 0 else 1, value if value >= 0 else -1 - value)
    if isinstance(value, str):
        data = value.encode("utf-8")
        return _cbor_encode_type_value(3, len(data)) + data
    if isinstance(value, list):
        return _cbor_encode_type_value(4, len(value)) + b"".join(cbor_encode(item) for item in value)
    if isinstance(value, dict):
        chunks = []
        for key, item in value.items():
            chunks.append(cbor_encode(str(key)))
            chunks.append(cbor_encode(item))
        return _cbor_encode_type_value(5, len(value)) + b"".join(chunks)
    raise TypeError(f"unsupported CBOR value: {type(value)!r}")


def _cbor_encode_type_value(major: int, value: int) -> bytes:
    prefix = major << 5
    if value < 24:
        return bytes([prefix | value])
    if value < 256:
        return bytes([prefix | 24, value])
    if value < 65536:
        return bytes([prefix | 25]) + value.to_bytes(2, "big")
    if value < 4294967296:
        return bytes([prefix | 26]) + value.to_bytes(4, "big")
    return bytes([prefix | 27]) + value.to_bytes(8, "big")


def cbor_decode(data: bytes) -> object:
    value, offset = _cbor_decode_one(data, 0)
    if offset != len(data):
        return value
    return value


def _cbor_decode_one(data: bytes, offset: int) -> tuple[object, int]:
    if offset >= len(data):
        raise CborDecodeError("unexpected end of CBOR")
    initial = data[offset]
    offset += 1
    major = initial >> 5
    additional = initial & 0x1F

    if major == 7:
        if additional == 20:
            return False, offset
        if additional == 21:
            return True, offset
        if additional in {22, 23}:
            return None, offset
        if additional == 24:
            return data[offset], offset + 1
        if additional == 25:
            return None, offset + 2
        if additional == 26:
            return struct.unpack(">f", data[offset : offset + 4])[0], offset + 4
        if additional == 27:
            return struct.unpack(">d", data[offset : offset + 8])[0], offset + 8
        return None, offset

    value, offset = _cbor_read_value(data, offset, additional)

    if major == 0:
        return value, offset
    if major == 1:
        return -1 - value, offset
    if major == 2:
        end = offset + value
        return data[offset:end], end
    if major == 3:
        end = offset + value
        return data[offset:end].decode("utf-8", errors="replace"), end
    if major == 4:
        items = []
        for _ in range(value):
            item, offset = _cbor_decode_one(data, offset)
            items.append(item)
        return items, offset
    if major == 5:
        obj = {}
        for _ in range(value):
            key, offset = _cbor_decode_one(data, offset)
            item, offset = _cbor_decode_one(data, offset)
            obj[key] = item
        return obj, offset
    raise CborDecodeError(f"unsupported CBOR major={major} additional={additional}")


def _cbor_read_value(data: bytes, offset: int, additional: int) -> tuple[int, int]:
    if additional < 24:
        return additional, offset
    if additional == 24:
        return data[offset], offset + 1
    if additional == 25:
        return int.from_bytes(data[offset : offset + 2], "big"), offset + 2
    if additional == 26:
        return int.from_bytes(data[offset : offset + 4], "big"), offset + 4
    if additional == 27:
        return int.from_bytes(data[offset : offset + 8], "big"), offset + 8
    raise CborDecodeError(f"unsupported additional value: {additional}")


def decode_body_sample(body: bytes) -> tuple[object | None, str]:
    if not body:
        return None, ""
    try:
        decoded = cbor_decode(body)
        return decoded, json.dumps(decoded, ensure_ascii=False)[:1000]
    except Exception:
        pass
    try:
        decoded = json.loads(body.decode("utf-8"))
        return decoded, json.dumps(decoded, ensure_ascii=False)[:1000]
    except Exception:
        return None, body[:200].hex(" ")


def resolve_url(clean_url: str) -> str:
    resolved = clean_url
    for marker, env_name in ENV_NAMES.items():
        value = os.environ.get(env_name) or VAR_DEFAULTS.get(marker, "")
        if marker in resolved and not value:
            raise ValueError(f"missing {env_name} for {marker}")
        resolved = resolved.replace(marker, value.rstrip("/"))
    return quote(resolved, safe=":/?&=%._-+,")


def headers_for(row: dict[str, str]) -> dict[str, str]:
    base_var = row["suggested_base_var"]
    is_admin = base_var == "{{admin_url}}"
    headers = {
        "accept": "application/json, text/plain, */*" if is_admin else "application/json",
        "d": os.environ.get("DEVICE", "25"),
        "lang": os.environ.get("ADMIN_LANG_HEADER" if is_admin else "LANG_HEADER", "en" if is_admin else "en_US"),
    }
    if is_admin:
        headers["client-id"] = os.environ.get("ADMIN_CLIENT_ID", "123")
        headers["client-version"] = os.environ.get("ADMIN_CLIENT_VERSION", "Chrome/151.0.0.0")
        device_id = os.environ.get("ADMIN_DEVICE_ID") or os.environ.get("X_DEVICE_ID")
        if device_id:
            headers["x-device-id"] = device_id
    token = ""
    if base_var == "{{admin_url}}":
        token = os.environ.get("ADMIN_TOKEN", "")
        prefix = os.environ.get("ADMIN_TOKEN_PREFIX", "")
        if token and prefix and not token.startswith(prefix):
            token = prefix + token
    elif base_var == "{{agency_url}}":
        token = os.environ.get("AGENCY_TOKEN", "")
    else:
        token = os.environ.get("API_TOKEN", "")
    if token:
        headers["t"] = token
    return headers


def read_rows(path: Path, limit: int) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            if "case_id" in row:
                rows.append(row)
            elif row["execution_policy"] == "safe_smoke":
                rows.append(row)
    return rows[:limit]


def get_nested(value: object, path: str) -> object:
    current = value
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def has_nested(value: object, path: str) -> bool:
    current = value
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return False
    return True


def assertion_result(result: dict[str, object], assertions: str) -> tuple[bool, list[str]]:
    failures = []
    body = result.get("decoded_body")
    rules = [item for item in assertions.split(",") if item]

    for rule in rules:
        if rule == "http_200":
            if result.get("status") != 200:
                failures.append("http status is not 200")
        elif rule == "decoded":
            if body is None:
                failures.append("body is not decoded")
        elif rule == "status_true":
            if not isinstance(body, dict) or body.get("status") is not True:
                failures.append("business status is not true")
        elif rule == "data_object":
            data = body.get("data") if isinstance(body, dict) else None
            if not isinstance(data, dict):
                failures.append("data is not object")
        elif rule == "data_list":
            data = body.get("data") if isinstance(body, dict) else None
            if not isinstance(data, list):
                failures.append("data is not list")
        elif rule.startswith("keys:"):
            keys = [item for item in rule.removeprefix("keys:").split("|") if item]
            for key in keys:
                if not has_nested(body, key):
                    failures.append(f"missing key {key}")

    return not failures, failures


def request_once(
    row: dict[str, str],
    timeout: float,
    insecure: bool,
    body: dict[str, object] | None = None,
    body_format: str = "json",
) -> dict[str, object]:
    url = resolve_url(row["clean_url"])
    headers = headers_for(row)
    payload = None
    if body is not None:
        if body_format == "cbor":
            payload = cbor_encode(body)
            headers["content-type"] = "application/cbor"
        else:
            payload = json.dumps(body).encode("utf-8")
            headers["content-type"] = "application/json"
    request = Request(url, data=payload, method=row["method"], headers=headers)
    context = ssl._create_unverified_context() if insecure else None
    started = time.monotonic()
    try:
        with urlopen(request, timeout=timeout, context=context) as response:
            body_bytes = response.read()
            elapsed_ms = int((time.monotonic() - started) * 1000)
            decoded, sample = decode_body_sample(body_bytes)
            return {
                "priority": row["priority"],
                "case_id": row.get("case_id", ""),
                "method": row["method"],
                "url": url,
                "status": response.status,
                "elapsed_ms": elapsed_ms,
                "ok": 200 <= response.status < 500,
                "decoded_body": decoded,
                "body_sample": sample,
            }
    except HTTPError as error:
        body_bytes = error.read()
        elapsed_ms = int((time.monotonic() - started) * 1000)
        decoded, sample = decode_body_sample(body_bytes)
        return {
            "priority": row["priority"],
            "case_id": row.get("case_id", ""),
            "method": row["method"],
            "url": url,
            "status": error.code,
            "elapsed_ms": elapsed_ms,
            "ok": error.code in {401, 403} or 200 <= error.code < 500,
            "decoded_body": decoded,
            "body_sample": sample,
        }
    except (URLError, TimeoutError, ValueError) as error:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        return {
            "priority": row["priority"],
            "case_id": row.get("case_id", ""),
            "method": row["method"],
            "url": url if "url" in locals() else row["clean_url"],
            "status": "ERROR",
            "elapsed_ms": elapsed_ms,
            "ok": False,
            "decoded_body": None,
            "body_sample": str(error),
        }


def login_row(clean_url: str, base_var: str, method: str = "POST") -> dict[str, str]:
    return {
        "priority": "LOGIN",
        "method": method,
        "clean_url": clean_url,
        "suggested_base_var": base_var,
    }


def extract_token(result: dict[str, object]) -> str:
    decoded = result.get("decoded_body")
    if not isinstance(decoded, dict):
        return ""
    if decoded.get("status") is not True:
        return ""
    data = decoded.get("data")
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        token = data.get("token") or data.get("t")
        return token if isinstance(token, str) else ""
    return ""


def client_login(args: argparse.Namespace) -> tuple[list[dict[str, object]], str]:
    phone = os.environ.get("CLIENT_PHONE", "")
    otp = os.environ.get("CLIENT_OTP", "")
    if not phone or not otp:
        raise SystemExit("CLIENT_PHONE and CLIENT_OTP are required")

    sms_row = login_row("{{api_url}}/member/sms", "{{api_url}}")
    sms_body = {
        "country_code": os.environ.get("CLIENT_COUNTRY_CODE", "63"),
        "phone": phone,
        "reason": "login",
    }
    sms_result = request_once(sms_row, args.timeout, args.insecure, sms_body, args.body_format)
    decoded = sms_result.get("decoded_body")
    otp_id = ""
    if isinstance(decoded, dict) and isinstance(decoded.get("data"), dict):
        otp_id = str(decoded["data"].get("id") or decoded["data"].get("otp_id") or "")

    login_result: dict[str, object] | None = None
    if otp_id:
        otp_row = login_row("{{api_url}}/member/otp/login/v2", "{{api_url}}")
        login_body = {
            "code": otp,
            "otp_id": otp_id,
        }
        login_result = request_once(otp_row, args.timeout, args.insecure, login_body, args.body_format)
        token = extract_token(login_result)
        if token:
            os.environ["API_TOKEN"] = token

    token = ""
    results = [sms_result]
    if login_result:
        token = extract_token(login_result)
        results.append(login_result)
    return results, token


def run_client_login(args: argparse.Namespace) -> None:
    results, token = client_login(args)
    Path(args.out).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {Path(args.out).resolve()}")
    print(f"client sms status={results[0]['status']} otp_id={'yes' if len(results) > 1 else 'no'}")
    if len(results) > 1:
        print(f"client login status={results[1]['status']} token={'yes' if token else 'no'}")


def admin_login(args: argparse.Namespace) -> tuple[list[dict[str, object]], str]:
    email = os.environ.get("ADMIN_EMAIL", "")
    password = os.environ.get("ADMIN_PASSWORD", "")
    google_code = os.environ.get("ADMIN_GOOGLE_CODE", "")
    if not email or not password or not google_code:
        raise SystemExit("ADMIN_EMAIL, ADMIN_PASSWORD, and ADMIN_GOOGLE_CODE are required")

    auth_row = login_row("{{admin_url}}/admin/login/auth", "{{admin_url}}")
    auth_body = {"email": email, "password": password}
    auth_result = request_once(auth_row, args.timeout, args.insecure, auth_body, args.body_format)

    login_row_data = login_row("{{admin_url}}/admin/login", "{{admin_url}}")
    login_body = {
        "email": email,
        "password": password,
        "google_code": int(google_code) if google_code.isdigit() else google_code,
        "google_secret": os.environ.get("ADMIN_GOOGLE_SECRET", ""),
    }
    if os.environ.get("ADMIN_CMPL"):
        login_body["cmpl"] = int(os.environ["ADMIN_CMPL"])
    login_result = request_once(login_row_data, args.timeout, args.insecure, login_body, args.body_format)
    token = extract_token(login_result)
    if token:
        os.environ["ADMIN_TOKEN"] = token

    results = [auth_result, login_result]
    return results, token


def run_admin_login(args: argparse.Namespace) -> None:
    results, token = admin_login(args)
    Path(args.out).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {Path(args.out).resolve()}")
    print(f"admin auth status={results[0]['status']}")
    print(f"admin login status={results[1]['status']} token={'yes' if token else 'no'}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", default="api/p0/interface-shortlist.csv")
    parser.add_argument("--env", default=".env")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--insecure", action="store_true", help="Disable TLS verification for test environments only")
    parser.add_argument("--body-format", choices=["json", "cbor"], default="json")
    parser.add_argument("--client-login", action="store_true")
    parser.add_argument("--admin-login", action="store_true")
    parser.add_argument("--with-client-login", action="store_true")
    parser.add_argument("--with-admin-login", action="store_true")
    parser.add_argument("--cases", default="", help="Run executable case CSV instead of shortlist CSV")
    parser.add_argument("--out", default="api/results/p0-smoke-result.json")
    args = parser.parse_args()

    load_env_file(Path(args.env))
    if args.client_login:
        run_client_login(args)
        return
    if args.admin_login:
        run_admin_login(args)
        return
    auth_results: list[dict[str, object]] = []
    if args.with_client_login:
        client_results, client_token = client_login(args)
        auth_results.extend(client_results)
        if client_token:
            os.environ["API_TOKEN"] = client_token
    if args.with_admin_login:
        admin_results, admin_token = admin_login(args)
        auth_results.extend(admin_results)
        if admin_token:
            os.environ["ADMIN_TOKEN"] = admin_token
    list_path = Path(args.cases or args.list)
    rows = read_rows(list_path, args.limit)
    if not args.execute:
        print("dry-run; add --execute to send requests")
        for row in rows:
            print(f"{row['priority']} {row['method']} {row['clean_url']} :: {row['source_file']}")
        return

    results = auth_results + [request_once(row, args.timeout, args.insecure) for row in rows]
    for row, result in zip(rows, results[len(auth_results) :]):
        assertions = row.get("assertions", "")
        if assertions:
            passed, failures = assertion_result(result, "http_200,decoded," + assertions)
            result["assertion_passed"] = passed
            result["assertion_failures"] = failures
    output = Path(args.out)
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    executable = [item for item in results if "assertion_passed" in item]
    passed = sum(1 for item in executable if item["assertion_passed"]) if executable else sum(1 for item in results if item["ok"])
    total = len(executable) if executable else len(results)
    print(f"wrote {output.resolve()}")
    print(f"ok {passed}/{total}")
    for item in results:
        label = item.get("case_id") or item["priority"]
        verdict = item.get("assertion_passed", item["ok"])
        print(f"{label} {item['status']} {item['elapsed_ms']}ms pass={verdict} {item['url']}")


if __name__ == "__main__":
    main()
