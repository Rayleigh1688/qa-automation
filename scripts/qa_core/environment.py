"""Local dotenv layering shared by Python entry points; no expansion or I/O at import."""
import os
from pathlib import Path


def read_values(path):
    values = {}
    for raw in Path(path).read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_environment(path, *, environ=None, required=True):
    shell = dict(os.environ if environ is None else environ)
    values = {}
    if Path(path).is_file():
        values.update(read_values(path))
    elif required:
        raise SystemExit('Environment file missing; copy config/environments/fat.env.example or uat.env.example to an ignored .env file.')
    personal = shell.get('QA_ENV_LOCAL')
    if personal:
        if not Path(personal).is_file():
            raise SystemExit('QA_ENV_LOCAL file missing; create the ignored personal file or unset QA_ENV_LOCAL.')
        values.update(read_values(personal))
    # Retain legacy file-wins default, but honour orchestration's explicit overrides.
    env = {**shell, **values}
    if shell.get('ENV_FILE_PRECEDENCE') == 'shell':
        env.update(shell)
    return env
