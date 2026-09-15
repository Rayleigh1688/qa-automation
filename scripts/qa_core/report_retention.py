"""Keep one finalized execution per environment within a requirement's report directory."""
import json
import os
from pathlib import Path
import re
import shutil


def _read(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


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
