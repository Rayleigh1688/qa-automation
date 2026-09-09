"""Shell-free executable selection shared by local runners."""
import os
from pathlib import Path
import shutil
import sys

WINDOWS = os.name == 'nt'
ROOT = Path(__file__).resolve().parents[2]


def process_command(command, *, project_root=None, environ=None):
    command = list(command)
    if not command:
        raise ValueError("command must not be empty")
    root = Path(project_root).resolve() if project_root is not None else ROOT
    env = os.environ if environ is None else environ
    node = shutil.which("node", path=env.get("PATH")) or "node"
    if command[0] in ('python', 'python3'):
        return [sys.executable, *command[1:]]
    if command[:2] == ['npx', 'playwright'] or command[0] == 'playwright':
        tail = command[2:] if command[0] == 'npx' else command[1:]
        return [node, str(root / 'node_modules/playwright/cli.js'), *tail]
    if command[0] == 'npm' and WINDOWS:
        cli = env.get('npm_execpath')
        if not cli or not Path(cli).is_file():
            node = shutil.which('node', path=env.get('PATH'))
            cli = str(Path(node).parent / 'node_modules/npm/bin/npm-cli.js') if node else ''
        if not cli or not Path(cli).is_file():
            raise OSError('npm CLI unavailable; launch through npm run')
        return [node, cli, *command[1:]]
    return command


def process_environment(env=None):
    return {**(os.environ if env is None else env), 'QA_PYTHON_EXECUTABLE': sys.executable}
