#!/usr/bin/env python3
"""Regenerate the latest UI business assertions/report without running any test."""
import json
from pathlib import Path
from ui_business_report import collect_assertions, render_report


def main():
    path = Path('ui/results/ui-business-run-status.json')
    state = json.loads(path.read_text())
    state['assertions'] = collect_assertions(state)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    path.chmod(0o600)
    render_report(state)
    print('Updated ui/reports/ui-business-report.html (existing evidence only; no tests run)')


if __name__ == '__main__':
    main()
