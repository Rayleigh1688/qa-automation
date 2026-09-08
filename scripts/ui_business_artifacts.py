"""One latest UI run; continuations retain the same run's evidence."""
import importlib.util
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def prepare_business_artifacts(*, resume=False, kyc_run_id='', root=Path('.')):
    if resume:
        return
    preserved = {}
    if kyc_run_id:
        for name in ('client-kyc-submit.json', 'kyc-ui-run-status.json'):
            path = root / 'ui/results' / name
            preserved[path] = path.read_bytes()
        submission, run = [json.loads(value) for value in preserved.values()]
        age = datetime.now(timezone.utc).timestamp() - datetime.fromisoformat(run['startedAt'].replace('Z', '+00:00')).timestamp()
        if not (submission.get('runId') == run.get('runId') == kyc_run_id and submission.get('status') == run.get('status') == 'APPROVED' and 0 <= age <= 3600):
            raise RuntimeError('Linked KYC evidence is stale or mismatched; previous results retained')
    if kyc_run_id:
        for item in submission.get('visualEvidence', {}).values():
            if item.get('privacy') != 'status_label_only' or item.get('runId') != kyc_run_id:
                continue
            path = root / item.get('path', '')
            allowed = [root / 'ui/results/screenshots' / name for name in ('kyc-submitted-status.png', 'kyc-approved-status.png')]
            if path not in allowed or not path.is_file() or path.is_symlink():
                continue
            content = path.read_bytes()
            if hashlib.sha256(content).hexdigest() == item.get('sha256'):
                preserved[path] = content
    spec = importlib.util.spec_from_file_location('artifact_cleaner', Path(__file__).with_name('clean-test-artifacts.py'))
    cleaner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cleaner)
    for directory in cleaner.TARGETS['ui']:
        cleaner.clean_dir(root / directory)
    for path, content in preserved.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        path.chmod(0o600)
    # Only API artifacts owned by this UI chain, not the independent API suite.
    (root / 'api/results/ui-fund-support.json').unlink(missing_ok=True)
    for path in (root / 'api/results/operations').glob('ui-kyc-approve.*'):
        path.unlink()
