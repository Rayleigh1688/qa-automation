#!/usr/bin/env python3
"""Plan and optionally execute fixed-unit UI bets until current turnover is covered.

FAT can query the database read-only. UAT uses read-only admin member/turnover
endpoints because its database is intentionally unavailable. The script never
updates wallet, turnover, or member state directly.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
from decimal import Decimal
from pathlib import Path


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if os.environ.get("ENV_FILE_PRECEDENCE") == "shell":
            os.environ.setdefault(key, value)
        else:
            os.environ[key] = value


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"missing required environment variable: {name}")
    return value


def unfinished_turnover_database(phone: str) -> Decimal:
    if not phone.isdigit():
        raise SystemExit("client phone must contain digits only")
    sql = (
        "SELECT COALESCE(SUM(CASE WHEN t.state=1 "
        "THEN GREATEST(t.turnover-t.finished,0) ELSE 0 END),0) "
        "FROM fb_members_turnover t "
        "JOIN fb_members m ON m.uid=t.uid "
        f"WHERE m.phone='{phone}';"
    )
    command = [
        "mysql",
        "--connect-timeout=8",
        "-h", required("DB_HOST"),
        "-P", required("DB_PORT"),
        "-u", required("DB_USER"),
        required("DB_NAME"),
        "-N",
        "-e", sql,
    ]
    mysql_env = os.environ.copy()
    mysql_env["MYSQL_PWD"] = required("DB_PASSWORD")
    result = subprocess.run(command, env=mysql_env, check=True, capture_output=True, text=True)
    return Decimal(result.stdout.strip() or "0")


def normalize_phone(value: object) -> str:
    return "".join(character for character in str(value or "") if character.isdigit())


def find_exact_member(value: object, phone: str) -> dict[str, object] | None:
    if isinstance(value, dict):
        if normalize_phone(value.get("phone")) == normalize_phone(phone):
            return value
        for item in value.values():
            found = find_exact_member(item, phone)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = find_exact_member(item, phone)
            if found:
                return found
    return None


def remaining_turnover(rows: object) -> Decimal:
    if not isinstance(rows, list):
        raise RuntimeError("admin turnover data.d is not a list")
    total = Decimal("0")
    for row in rows:
        if not isinstance(row, dict) or int(row.get("state") or 0) != 1:
            continue
        turnover = Decimal(str(row.get("turnover") or "0"))
        finished = Decimal(str(row.get("finished") or "0"))
        total += max(turnover - finished, Decimal("0"))
    return total


def import_smoke_runner():
    scripts_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(scripts_dir))
    module_path = scripts_dir / "api-smoke-runner.py"
    spec = importlib.util.spec_from_file_location("p0_api_smoke_runner", module_path)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot import {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AdminTurnoverReader:
    def __init__(self, phone: str, session_in: str, timeout: float, insecure: bool):
        self.phone = phone
        self.timeout = timeout
        self.insecure = insecure
        self.smoke = import_smoke_runner()
        from p0_session import load_session

        load_session(session_in, phone)
        self._ensure_admin_session()
        self.uid = self._find_uid()

    @staticmethod
    def row(url: str, method: str = "GET") -> dict[str, str]:
        return {
            "priority": "TURNOVER_READ",
            "method": method,
            "clean_url": url,
            "suggested_base_var": "{{admin_url}}",
        }

    def request(self, url: str, method: str = "GET", body: dict[str, object] | None = None) -> dict[str, object]:
        result = self.smoke.request_once(
            self.row(url, method), self.timeout, self.insecure, body, "cbor"
        )
        decoded = result.get("decoded_body")
        if result.get("status") != 200 or not isinstance(decoded, dict) or decoded.get("status") is not True:
            raise RuntimeError(f"admin read failed: method={method} status={result.get('status')}")
        return decoded

    def _ensure_admin_session(self) -> None:
        try:
            self.request("{{admin_url}}/admin/me/detail")
            return
        except RuntimeError:
            pass
        login_args = argparse.Namespace(timeout=self.timeout, insecure=self.insecure, body_format="cbor")
        _, token = self.smoke.admin_login(login_args)
        if not token:
            raise RuntimeError("admin login failed while preparing turnover reader")

    def _find_uid(self) -> str:
        decoded = self.request(
            "{{admin_url}}/admin/member/list",
            "POST",
            {"page": 1, "page_size": 10, "phone": self.phone},
        )
        member = find_exact_member(decoded.get("data"), self.phone)
        uid = member.get("uid") if member else None
        if uid is None or str(uid).strip() == "":
            raise RuntimeError("exact member was not found in admin member list")
        return str(uid)

    def unfinished(self) -> Decimal:
        page = 1
        page_size = 100
        rows: list[object] = []
        while page <= 100:
            decoded = self.request(
                f"{{{{admin_url}}}}/admin/finance/turnover/list?uid={self.uid}&page={page}&page_size={page_size}"
            )
            data = decoded.get("data")
            if not isinstance(data, dict):
                raise RuntimeError("admin turnover data is not an object")
            batch = data.get("d")
            if not isinstance(batch, list):
                raise RuntimeError("admin turnover data.d is not a list")
            rows.extend(batch)
            total = int(data.get("t") or len(rows))
            if len(rows) >= total or len(batch) < page_size:
                return remaining_turnover(rows)
            page += 1
        raise RuntimeError("admin turnover pagination exceeded safety cap")


def choose_turnover_source(requested: str, env_path: str) -> str:
    configured = os.environ.get("TURNOVER_SOURCE", "").strip().lower()
    selected = requested if requested != "auto" else configured
    if selected and selected != "auto":
        if selected not in {"database", "admin"}:
            raise SystemExit("turnover source must be auto, database, or admin")
        return selected
    return "admin" if "uat" in Path(env_path).name.lower() else "database"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=os.environ.get("ENV_FILE", ".env.fat"))
    parser.add_argument("--phone", default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--bet-unit", type=int)
    parser.add_argument("--max-spins", type=int, default=20)
    parser.add_argument("--poll-interval", type=float, default=5)
    parser.add_argument("--poll-timeout", type=float, default=60)
    parser.add_argument("--game-id", default="")
    parser.add_argument("--game-page", default="")
    parser.add_argument("--turnover-source", choices=["auto", "database", "admin"], default="auto")
    parser.add_argument("--session-in", default="api/results/p0-api-session.json")
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--insecure", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--out", default="ui/results/turnover-bet-plan.json")
    args = parser.parse_args()

    load_env_file(Path(args.env))
    args.bet_unit = args.bet_unit or int(os.environ.get("CLIENT_GAME_BET_AMOUNT", "1000"))
    args.game_id = args.game_id or os.environ.get("CLIENT_GAME_ID", "beanstalk_243")
    args.game_page = args.game_page or os.environ.get("CLIENT_GAME_PAGE_PATH", "/s-game-page/17453877442826")
    phone = args.phone or os.environ.get("BET_CLIENT_PHONE") or os.environ.get("WRITE_CLIENT_PHONE") or os.environ.get("CLIENT_PHONE", "")
    password = args.password or os.environ.get("BET_CLIENT_PASSWORD") or os.environ.get("WRITE_CLIENT_PASSWORD") or os.environ.get("CLIENT_PASSWORD", "")
    if not phone or not password:
        raise SystemExit("phone and password are required")
    if args.bet_unit <= 0 or args.max_spins <= 0:
        raise SystemExit("bet unit and max spins must be positive")

    source = choose_turnover_source(args.turnover_source, args.env)
    if source == "admin":
        turnover_reader = AdminTurnoverReader(phone, args.session_in, args.timeout, args.insecure)
        unfinished_turnover = turnover_reader.unfinished
    else:
        unfinished_turnover = lambda: unfinished_turnover_database(phone)

    before = unfinished_turnover()
    initial_planned_spins = math.ceil(before / Decimal(args.bet_unit)) if before > 0 else 0
    if initial_planned_spins > args.max_spins:
        raise SystemExit(
            f"planned spins {initial_planned_spins} exceed safety cap {args.max_spins}; "
            "raise --max-spins only after reviewing balance and turnover"
        )

    executed = False
    total_planned = 0
    total_completed = 0
    batches: list[dict[str, object]] = []
    current = before
    while args.execute and current > 0:
        batch_spins = math.ceil(current / Decimal(args.bet_unit))
        if total_planned + batch_spins > args.max_spins:
            raise SystemExit(
                f"total planned spins {total_planned + batch_spins} exceed safety cap {args.max_spins}"
            )
        ui_env = os.environ.copy()
        ui_env.update({
            "ENV_FILE": args.env,
            "ENV_FILE_PRECEDENCE": "shell",
            "CLIENT_PHONE": phone,
            "CLIENT_PASSWORD": password,
            "CLIENT_GAME_ID": args.game_id,
            "CLIENT_GAME_PAGE_PATH": args.game_page,
            "CLIENT_GAME_BET_AMOUNT": str(args.bet_unit),
            "CLIENT_GAME_SPIN_COUNT": str(batch_spins),
            "EXECUTE_BET": "true",
            "CLIENT_REUSE_P0_AUTH": "true",
            "CLIENT_AUTH_MODE": os.environ.get("CLIENT_AUTH_MODE", "password"),
        })
        batch_before = current
        command = ["npm", "run", "test:ui:game-bet"]
        if os.environ.get("PRESERVE_UI_RESULTS") == "true":
            command = [
                "npx", "playwright", "test",
                "ui/cases/client-game-bet-smoke.spec.mjs", "--workers=1",
            ]
        subprocess.run(command, env=ui_env, check=True)
        game_result = json.loads(Path("ui/results/client-game-bet-smoke.json").read_text(encoding="utf-8"))
        completed_spins = int(game_result.get("completedSpinCount") or 0)
        total_planned += batch_spins
        total_completed += completed_spins
        executed = True

        deadline = time.monotonic() + args.poll_timeout
        observed = unfinished_turnover()
        while observed > 0 and time.monotonic() < deadline:
            time.sleep(max(0.5, args.poll_interval))
            observed = unfinished_turnover()
        batches.append({
            "turnover_before": str(batch_before),
            "planned_spins": batch_spins,
            "completed_spins": completed_spins,
            "turnover_after_poll": str(observed),
        })
        if observed >= batch_before:
            current = observed
            break
        current = observed

    after = current if executed else before
    result = {
        "phone_suffix": phone[-4:],
        "turnover_source": source,
        "bet_unit": args.bet_unit,
        "turnover_before": str(before),
        "planned_spins": total_planned if executed else initial_planned_spins,
        "completed_spins": total_completed,
        "executed": executed,
        "turnover_after": str(after),
        "turnover_cleared": after == 0,
        "batches": batches,
    }
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    if executed and after > 0:
        raise SystemExit(f"turnover remains after UI bets: {after}")


if __name__ == "__main__":
    main()
