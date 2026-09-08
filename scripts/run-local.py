#!/usr/bin/env python3
"""Hold the local run lock across a complete command, including nested npm scripts."""
import argparse
import sys
import json
import os
import shlex
from pathlib import Path
from qa_core.terminal import print_result
from qa_core.local_lock import local_run_lock, LocalRunBusy
from ui_process import run_ui_process


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', help='Named repository command')
    parser.add_argument('--shell', help='Repository npm command; extra arguments are passed literally')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command[:1] == ['--']:
        command = command[1:]
    stages = [command]
    if args.task:
        recipes = json.loads((Path(__file__).resolve().parents[1] / 'config/local-commands.json').read_text())
        if args.task not in recipes:
            parser.error('unknown repository task')
        stages = recipes[args.task]
        stages[-1].extend(command)
    elif args.shell:
        # Legacy repository recipe syntax only; never invoke a system shell.
        stages = [shlex.split(part) for part in args.shell.split(' && ')]
        stages[-1].extend(command)
    command = stages[-1]
    if not command:
        parser.error('supply a command after --')
    try:
        with local_run_lock() as fd:
            for stage in stages:
                env = dict(os.environ)
                while stage and '=' in stage[0] and stage[0].split('=', 1)[0].isidentifier():
                    key, value = stage.pop(0).split('=', 1)
                    env[key] = value
                if not stage:
                    parser.error('empty command stage')
                code = run_ui_process(stage, env=env, pass_fds=(() if fd is None else (fd,))).returncode
                if code:
                    return code
            return 0
    except LocalRunBusy as error:
        print_result(f'BLOCKED: {error}', 'BLOCKED', file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    except OSError:
        print_result('BLOCKED: command or local lock unavailable; check installation and local permissions.', 'BLOCKED', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
