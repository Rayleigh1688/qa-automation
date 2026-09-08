#!/usr/bin/env python3
"""Hold the local run lock across a complete command, including nested npm scripts."""
import argparse
import sys
from qa_core.terminal import print_result
from qa_core.local_lock import local_run_lock, LocalRunBusy
from ui_process import run_ui_process


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shell', help='Repository npm command; extra arguments are passed literally')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command[:1] == ['--']:
        command = command[1:]
    if args.shell:
        command = ['/bin/sh', '-c', args.shell + ' "$@"', 'qa-local', *command]
    if not command:
        parser.error('supply a command after --')
    try:
        with local_run_lock() as fd:
            return run_ui_process(command, pass_fds=(() if fd is None else (fd,))).returncode
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
