#!/usr/bin/env python3
"""Export per-story business overviews and API data tables, entirely offline."""
import argparse
import json
from pathlib import Path
import re

from qa_core.case_catalogue import export_catalogues
from qa_core.execution_plan import load

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stories', nargs='*')
    parser.add_argument('--all', action='store_true', help='Export every requirement design')
    args = parser.parse_args()
    if args.all == bool(args.stories):
        parser.error('select story IDs or --all')
    stories = sorted(p.name for p in (ROOT / 'requirements').glob('ISOP-*') if p.is_dir()) if args.all else args.stories
    for story in stories:
        if not re.fullmatch(r'ISOP-\d+', story):
            parser.error('invalid story ID')
        folder = ROOT / 'requirements' / story
        plan = cases = suite = None
        if (folder / 'plan.json').is_file():
            from filbet.requirement_adapter import METHODS
            plan, cases, _ = load(folder / 'plan.json', METHODS)
        elif (folder / 'api/cases.json').is_file():
            suite = json.loads((folder / 'api/cases.json').read_text(encoding='utf-8'))
        overview, data = export_catalogues(folder, plan=plan, cases=cases, suite=suite)
        print(f'{story}: overview={overview}; API data={data if data is not None else "not implemented"}; no login')


if __name__ == '__main__':
    main()
