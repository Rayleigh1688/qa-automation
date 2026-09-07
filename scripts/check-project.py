#!/usr/bin/env python3
"""Offline navigation and syntax checks; never import runners or read env files."""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def project_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root, check=True, capture_output=True,
    )
    return sorted({root / name for name in result.stdout.decode().split("\0") if name and (root / name).is_file()})


def document_errors(path: Path, root: Path, commands: set[str]) -> list[str]:
    errors = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        label = f"{path.relative_to(root)}:{number}"
        for target in re.findall(r"\]\(([^)]+)\)", line):
            target = target.strip().split(' "', 1)[0].strip("<>").split("#", 1)[0]
            if not target or re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                continue
            resolved = (path.parent / unquote(target)).resolve()
            generated_roots = ("api/results", "ui/results", "ui/reports", "playwright-report", "test-results")
            if any(resolved.is_relative_to(root.resolve() / entry) for entry in generated_roots):
                continue  # Latest-run artifacts are optional and routinely cleaned.
            if not resolved.exists():
                errors.append(f"{label}: missing link target {target}")
        for command in re.findall(r"npm run ([\w:-]+)", line):
            if command not in commands:
                errors.append(f"{label}: unknown npm command {command}")
        # Skill routes use code spans rather than Markdown links.
        if path.name == "SKILL.md":
            for target in re.findall(r"`(\.\./[^`]+)`", line):
                if not (path.parent / target).exists():
                    errors.append(f"{label}: missing skill route {target}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("docs", "syntax"))
    args = parser.parse_args()
    files = project_files(ROOT)
    errors = []
    count = 0
    commands = set(json.loads((ROOT / "package.json").read_text())["scripts"])
    for path in files:
        parts = path.relative_to(ROOT).parts
        if args.mode == "docs":
            if path.suffix != ".md" or "results" in parts or parts[:2] == ("docs", "history") or parts[:3] == ("archive", "interface-scans", "2026-09-07"):
                continue
            errors.extend(document_errors(path, ROOT, commands))
        elif path.suffix == ".py":
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError as error:
                errors.append(f"{path.relative_to(ROOT)}:{error.lineno}: {error.msg}")
        elif path.suffix in {".mjs", ".js"}:
            result = subprocess.run(["node", "--check", str(path)], cwd=ROOT, capture_output=True, text=True)
            if result.returncode:
                errors.append(result.stderr.strip())
        else:
            continue
        count += 1
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"{args.mode} checks PASS: {count} files")


if __name__ == "__main__":
    main()
