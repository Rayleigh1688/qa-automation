#!/usr/bin/env python3
"""Run API suites by level.

Examples:
    python3 scripts/run-api-tests.py p0
    python3 scripts/run-api-tests.py p0 p1
    python3 scripts/run-api-tests.py p0 --safe-only
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(command: list[str]) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, check=True)


def clean_api_results() -> None:
    run(["python3", "scripts/clean-test-artifacts.py", "api"])


def render_p0_main_report(args: argparse.Namespace) -> None:
    run(
        [
            "python3",
            "scripts/render-main-flow-report.py",
            "--scope",
            args.scope,
            "--out",
            "api/results/p0-main-flow-report.md",
            "--html-out",
            "api/results/p0-api-report.html",
        ]
    )


def run_p0(args: argparse.Namespace) -> None:
    cases = Path("api/p0/test-cases.csv")
    if not cases.exists():
        raise SystemExit("missing api/p0/test-cases.csv")

    run(
        [
            "python3",
            "scripts/api-smoke-runner.py",
            "--cases",
            str(cases),
            "--with-client-login",
            "--with-admin-login",
            "--limit",
            "0",
            "--execute",
            "--body-format",
            args.body_format,
            "--out",
            "api/results/p0-smoke-result.json",
            "--session-out",
            "api/results/p0-api-session.json",
            "--session-in",
            "api/results/p0-api-session.json",
            *(["--insecure"] if args.insecure else []),
        ]
    )
    run(
        [
            "python3",
            "scripts/render-p0-smoke-report.py",
            "--result",
            "api/results/p0-smoke-result.json",
            "--cases",
            str(cases),
            "--out",
            "api/results/p0-smoke-report.md",
            "--scope",
            args.scope,
        ]
    )
    run(
        [
            "python3",
            "scripts/api-p0-negative-runner.py",
            "--body-format",
            args.body_format,
            "--scope",
            args.scope,
            "--out",
            "api/results/p0-negative-result.json",
            "--report",
            "api/results/p0-negative-report.md",
            "--session-in",
            "api/results/p0-api-session.json",
            *(["--insecure"] if args.insecure else []),
        ]
    )
    write_error: subprocess.CalledProcessError | None = None
    if not args.safe_only:
        try:
            run(
                [
                    "python3",
                    "scripts/api-controlled-flow-runner.py",
                    "--deposit",
                    "--approve-deposit",
                    "--body-format",
                    args.body_format,
                    *(["--register-phone", args.register_phone] if args.register_phone else []),
                    *(["--client-phone", args.write_client_phone] if args.write_client_phone else []),
                    *(["--client-otp", args.write_client_otp] if args.write_client_otp else []),
                    "--deposit-pid",
                    args.deposit_pid,
                    "--deposit-amount",
                    args.deposit_amount,
                    "--out",
                    "api/results/fund-flow-seed-result.json",
                    "--session-in",
                    "api/results/p0-api-session.json",
                    "--session-out",
                    "api/results/p0-api-session.json",
                    *(["--insecure"] if args.insecure else []),
                ]
            )
        except subprocess.CalledProcessError as error:
            write_error = error
    render_p0_main_report(args)
    if write_error:
        raise write_error


def run_generic_level(level: str, args: argparse.Namespace) -> None:
    cases = Path(f"api/{level}/test-cases.csv")
    if not cases.exists():
        print(f"skip {level}: missing {cases}")
        return
    output = f"api/results/{level}-smoke-result.json"
    report = f"api/results/{level}-smoke-report.md"
    run(
        [
            "python3",
            "scripts/api-smoke-runner.py",
            "--cases",
            str(cases),
            "--with-client-login",
            "--with-admin-login",
            "--execute",
            "--body-format",
            args.body_format,
            "--out",
            output,
            *(["--insecure"] if args.insecure else []),
        ]
    )
    run(
        [
            "python3",
            "scripts/render-p0-smoke-report.py",
            "--result",
            output,
            "--cases",
            str(cases),
            "--out",
            report,
            "--title",
            f"{level.upper()} API Smoke Report",
            "--scope",
            args.scope,
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("levels", nargs="+", help="test levels to run, for example: p0 p1")
    parser.add_argument("--scope", default="FAT")
    parser.add_argument("--body-format", choices=["json", "cbor"], default="cbor")
    parser.add_argument("--insecure", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--include-write", action="store_true", help="compatibility flag; P0 already includes controlled deposit seeding by default")
    parser.add_argument("--safe-only", action="store_true", help="skip controlled P0 writes and run only read/negative checks")
    parser.add_argument("--no-clean", action="store_true", help="preserve existing controlled-flow evidence while refreshing repeatable gates")
    parser.add_argument("--deposit-pid", default="47870534954254469")
    parser.add_argument("--deposit-amount", default="1200")
    parser.add_argument("--withdraw-amount", default="1000")
    parser.add_argument("--write-client-phone", default="")
    parser.add_argument("--write-client-otp", default="")
    parser.add_argument("--withdraw-client-phone", default="")
    parser.add_argument("--withdraw-client-otp", default="")
    parser.add_argument("--register-phone", default="")
    args = parser.parse_args()

    if args.safe_only and args.include_write:
        raise SystemExit("--safe-only and --include-write cannot be used together")

    if not args.no_clean:
        clean_api_results()

    for level in [item.lower() for item in args.levels]:
        if level == "p0":
            try:
                run_p0(args)
            except subprocess.CalledProcessError:
                # A failing smoke/negative/write step must still leave a P0
                # verdict artifact for local inspection and CI archiving.
                render_p0_main_report(args)
                raise
        elif level in {"p1", "p2"}:
            run_generic_level(level, args)
        else:
            raise SystemExit(f"unsupported level: {level}")


if __name__ == "__main__":
    main()
