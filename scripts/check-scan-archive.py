#!/usr/bin/env python3
"""Verify the frozen scan relocation without executing archived scripts."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'archive/interface-scans/2026-09-07'


def main():
    records = json.loads((ARCHIVE / 'manifest.json').read_text())['files']
    errors = []
    seen = set()
    for record in records:
        path = (ROOT / record['archived']).resolve()
        if not path.is_relative_to(ARCHIVE) or path in seen:
            errors.append('Invalid or duplicate archive path')
            continue
        seen.add(path)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256_archived']:
            errors.append(f"Missing or changed: {record['archived']}")
        if (ROOT / record['original']).exists():
            errors.append(f"Old location still exists: {record['original']}")
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'archive checks PASS: {len(records)} manifest files')


if __name__ == '__main__':
    main()
