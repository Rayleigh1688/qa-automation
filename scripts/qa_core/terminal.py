"""Terminal-only styling; never change result values or persisted reports."""
import os
import sys


def styled(text, kind, *, stream=None):
    stream = sys.stdout if stream is None else stream
    if 'NO_COLOR' in os.environ or os.environ.get('TERM') == 'dumb' or not getattr(stream, 'isatty', lambda: False)():
        return str(text)
    codes = {'PASS': '1;32', 'FAIL': '1;31', 'FAILED': '1;31', 'ERROR': '1;31',
             'BLOCKED': '1;31', 'INTERRUPTED': '1;31', 'WARN': '1;33',
             'SKIPPED': '1;33', 'NOT_RUN': '1;33', 'PATH': '4;36'}
    code = codes.get(str(kind).upper())
    return f'\033[{code}m{text}\033[0m' if code else str(text)


def print_result(text, status, *, file=None, flush=True):
    stream = sys.stdout if file is None else file
    print(styled(text, status, stream=stream), file=stream, flush=flush)


def print_path(text, *, file=None, flush=True):
    print_result(text, 'PATH', file=file, flush=flush)
