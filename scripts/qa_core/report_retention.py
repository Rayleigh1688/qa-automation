"""Retention for finalized execution reports and their regenerable views."""
import json
import os
from pathlib import Path
import re
import shutil

RUN_NAME = re.compile(r'\d{8}T\d{6}Z-[a-f0-9]{8}')
API_VIEW_FILES = ('results.html', 'results.csv', 'cases.csv', 'failures.csv', 'pending.csv', 'summary.json')


def _read(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def _regular_file(path):
    return not path.is_symlink() and path.is_file()


def _completed_api_run(folder):
    if folder.is_symlink() or not folder.is_dir() or not RUN_NAME.fullmatch(folder.name):
        return None
    raw = folder / 'result.json'
    snapshot = folder / 'cases.snapshot.json'
    if not all(_regular_file(path) for path in (raw, snapshot, folder / 'plan.snapshot.json')):
        return None
    report = _read(raw)
    cases = _read(snapshot)
    if not isinstance(report, dict) or not isinstance(cases, list):
        return None
    timings = report.get('timings_ms')
    if (report.get('mode') != 'execution' or report.get('schema_version') != 2
            or report.get('requirement') != folder.parent.name or report.get('run_id') != folder.name
            or report.get('environment') not in ('FAT', 'UAT') or report.get('profile')
            or report.get('execution_methods') or report.get('report_owner') == 'orchestration'
            or not isinstance(timings, dict) or 'report' not in timings or timings.get('ui')
            or not cases or not all(isinstance(case, dict) and case.get('类型') == 'API' for case in cases)
            or (folder / 'team-packet').exists()):
        return None
    return report


def _indexed_run_names(index_paths, story):
    names = set()
    for path in index_paths:
        if path.parent.is_symlink() or not _regular_file(path):
            continue
        indexed = _read(path)
        if not isinstance(indexed, dict) or not isinstance(indexed.get('raw'), str):
            continue
        raw = Path(indexed['raw'])
        name = raw.parent.name
        if raw.name == 'result.json' and raw.parent.parent.name == story and name == indexed.get('run_id'):
            names.add(name)
    return names


def remove_previous_api_views(folder, *, index_paths=()):
    """Remove generated views of previous standalone API runs, retaining their evidence."""
    folder = Path(folder)
    if not re.fullmatch(r'ISOP-\d+', folder.parent.name) or any(
        path.is_symlink() for path in (folder.parent, folder.parent.parent, folder.parent.parent.parent)
    ):
        return []
    current = _completed_api_run(folder)
    if current is None or not all(_regular_file(folder / name) for name in ('results.html', 'results.csv')):
        raise ValueError('publish a completed API report before cleanup')
    protected = _indexed_run_names(index_paths, folder.parent.name)
    removed = []
    for child in sorted(folder.parent.iterdir()):
        if child == folder or child.name in protected:
            continue
        report = _completed_api_run(child)
        if report is None or report['environment'] != current['environment']:
            continue
        for name in API_VIEW_FILES:
            view = child / name
            if _regular_file(view):
                view.unlink(missing_ok=True)
                removed.append(view)
    return removed


def retain_latest(folder, *, state_dir):
    folder = Path(folder)
    parent = folder.parent
    if folder.is_symlink() or not re.fullmatch(r'ISOP-\d+', parent.name):
        raise ValueError('retention requires a real requirement run directory')
    current = _read(folder / 'result.json')
    if current.get('mode') not in {'execution', 'evidence-summary'} or current.get('environment') not in {'FAT', 'UAT'} or not (folder / 'results.html').is_file():
        raise ValueError('publish a completed report before cleanup')
    candidates = []
    for child in parent.iterdir():
        if child.is_symlink() or not child.is_dir():
            continue
        report = _read(child / 'result.json')
        if report.get('mode') in {'execution', 'evidence-summary'} and report.get('environment') in {'FAT', 'UAT'}:
            candidates.append((child, report))
    kept = {}
    for child, report in sorted(candidates, key=lambda pair: pair[1].get('source_time', '')):
        if (child / 'results.html').is_file():
            kept[report['environment']] = child
    kept[current['environment']] = folder
    removed = [child for child, _ in candidates if child not in kept.values()]
    # Keep only operational identifiers, never credentials or historical report bodies.
    archive_identifiers(removed, state_dir=state_dir, story=parent.name)
    for env, child in kept.items():
        value = {'run_id': child.name, 'results': child.name + '/results.html', 'raw': child.name + '/result.json'}
        (parent / ('latest-' + env.lower() + '.json')).write_text(json.dumps(value) + '\n')
        (parent / ('latest-' + env.lower() + '.html')).write_text('<!doctype html><meta charset="utf-8"><title>' + env + '最新报告</title><a href="' + value['results'] + '">打开' + env + '最新报告</a>')
    for child in removed:
        shutil.rmtree(child)
    return [p.name for p in removed]


def archive_identifiers(folders, *, state_dir, story):
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / ('report-records-' + story.lower() + '.json')
    ledger = _read(path)
    for folder in folders:
        records = _read(folder / 'private-checkpoints.json')
        if not isinstance(records, list):
            continue
        rows = []
        for item in records:
            if not isinstance(item, dict):
                continue
            safe = {key: item[key] for key in ('case', 'step', 'uid', 'phone', 'pending', 'processed') if key in item}
            if any(key in safe for key in ('uid', 'phone', 'pending', 'processed')):
                rows.append(safe)
        if rows:
            ledger[folder.name] = rows
    fd = os.open(path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(ledger, stream, ensure_ascii=False, indent=2)
    path.chmod(0o600)
