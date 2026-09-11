#!/usr/bin/env python3
"""Validate a CSV catalogue or render recorded results. No network/business writes."""
import argparse
import json
from pathlib import Path
from qa_core.case_report import load_cases, write_views


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', required=True)
    parser.add_argument('--results')
    parser.add_argument('--out')
    args = parser.parse_args()
    cases = load_cases(args.cases)
    if not args.results and not args.out:
        print(f'Case catalogue PASS: {len(cases)} cases')
        return 0
    if not args.results or not args.out:
        parser.error('--results and --out must be supplied together')
    report = json.loads(Path(args.results).read_text(encoding='utf-8-sig'))
    summary = write_views(args.out, cases, report)
    print(json.dumps(summary, ensure_ascii=False))
    print(Path(args.out) / 'results.html')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
