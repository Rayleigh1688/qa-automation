#!/usr/bin/env python3
"""Run the default P0 UI suite and always render the shared UI report."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


DEFAULT_SPECS = [
    "ui/cases/client-login.spec.mjs",
    "ui/cases/client-main-flow.spec.mjs",
    "ui/cases/client-deposit-contract.spec.mjs",
    "ui/cases/client-game-bet-smoke.spec.mjs",
    "ui/cases/client-p0-positive-negative.spec.mjs",
]


def run(command: list[str], env: dict[str, str]) -> int:
    print("+ " + " ".join(command), flush=True)
    try:
        return subprocess.run(command, env=env, check=False).returncode
    except OSError as error:
        print(f"command unavailable: {error}", flush=True)
        return 127


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=os.environ.get("ENV_FILE", ".env.fat"))
    parser.add_argument("--scope", default="")
    parser.add_argument("--no-clean", action="store_true")
    args = parser.parse_args()
    scope = args.scope.upper() if args.scope else ("UAT" if ".uat" in Path(args.env).name.lower() else "FAT")
    env = {**os.environ, "ENV_FILE": args.env, "CLIENT_REUSE_P0_AUTH": "true"}
    clean_code = 0
    if not args.no_clean:
        clean_code = run(["python3", "scripts/clean-test-artifacts.py", "ui"], env)
    test_code = clean_code or run(["npx", "playwright", "test", *DEFAULT_SPECS, "--workers=1"], env)
    report_code = run([
        "python3", "scripts/render-ui-p0-report.py", "--scope", scope,
        "--html-out", "ui/reports/p0-ui-report.html",
    ], env)
    print(
        f"P0 UI run status={'PASS' if test_code == 0 else 'FAILED'}",
        flush=True,
    )
    print(f"HTML report: {Path('ui/reports/p0-ui-report.html').resolve().as_uri()}", flush=True)
    return test_code or report_code


if __name__ == "__main__":
    raise SystemExit(main())
