#!/usr/bin/env python3
"""Keep check:archive compatible and prevent retired scan payloads returning."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'archive/interface-scans'


def main():
    if not (ARCHIVE / 'README.md').is_file():
        raise SystemExit('Missing scan retirement index')
    unexpected = [p.relative_to(ROOT) for p in ARCHIVE.iterdir() if p.name != 'README.md']
    if unexpected:
        raise SystemExit('Retired scan payloads must not return: ' + ', '.join(map(str, unexpected)))
    print('archive checks PASS: retirement index only; current assets in api/inventory and api/catalog')


if __name__ == '__main__':
    main()
