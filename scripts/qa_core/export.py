"""Export an explicit runtime source allowlist; never traverse project data."""
import hashlib
import json
from pathlib import Path
import shutil

CORE_FILES = (
    '__init__.py', 'codec.py', 'environment.py', 'local_lock.py', 'process.py',
    'process_command.py', 'windows_job.py', 'terminal.py', 'workflow.py', 'reporting.py',
    'redaction.py', 'values.py', 'case_report.py', 'case_catalogue.py', 'execution_plan.py', 'plan_runner.py', 'team_delivery.py', 'ui_contract.py', 'json_worker.py',
)
JS_FILES = ('python-runtime.mjs', 'python-launcher.mjs')


def export_runtime(destination):
    """Create a new destination directory. Existing paths are never overwritten."""
    destination = Path(destination)
    core = Path(__file__).resolve().parent
    sources = [(core/name, Path('scripts/qa_core')/name) for name in CORE_FILES]
    sources += [(core.parent/name, Path('scripts')/name) for name in JS_FILES]
    guide = core.parents[1] / 'docs/runtime-reuse.md'
    sources.append((guide, Path('README.md')))
    for source, _ in sources:
        if not source.is_file():
            raise FileNotFoundError('runtime export source missing')
    destination.mkdir(parents=True, exist_ok=False)
    manifest = {'format_version': 1, 'files': {}}
    for source, relative in sources:
        output = destination/relative
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, output)
        manifest['files'][relative.as_posix()] = hashlib.sha256(output.read_bytes()).hexdigest()
    (destination/'runtime-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    return manifest
