"""Offline file policy over worktrees, the index, and every newly pushed commit.

Only paths, object IDs and byte counts are reported. Git payloads are never printed.
This is a repository hygiene check, not a content/secret scanner.
"""
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess


MIB = 1024 * 1024
POLICY_PATH = 'config/repository-file-policy.json'
DEPENDENCY_DIRS = {
    'node_modules', '.venv', 'venv', '__pycache__', 'site-packages',
    '.cache', '.pytest_cache', '.mypy_cache', '.ruff_cache', 'bower_components',
}
OUTPUT_DIRS = {
    'screenshots', 'videos', 'playwright-report', 'test-results', 'blob-report',
    'coverage', '.playwright', 'logs', 'raw-responses', 'raw_responses',
}
RAW_NAMES = {
    'result.json', 'results.json', 'raw-response.json', 'raw-responses.json',
    'raw_response.json', 'raw_responses.json', 'packet.json', 'plan.snapshot.json',
    'cases.snapshot.json', 'auth.json', 'storage_state.json',
}
PLACEHOLDERS = {'api/results/.gitkeep', 'ui/results/.gitkeep', 'ui/reports/.gitkeep'}
NEWLINE_BLOBS = {hashlib.new(algorithm, b'blob 1\0\n').hexdigest() for algorithm in ('sha1', 'sha256')}
SOURCE_CSV_ROOTS = ('api/inventory/', 'api/catalog/', 'api/p0/')


class FilePolicyError(ValueError):
    """A safe, non-payload diagnostic; callers must fail closed."""


def valid_path(path):
    return (isinstance(path, str) and bool(path) and not path.startswith('/')
            and '\\' not in path and all(p not in {'', '.', '..'} for p in path.split('/')))


def forbidden_reason(path):
    parts = PurePosixPath(path).parts
    lowered = tuple(p.lower() for p in parts)
    name = lowered[-1]
    if set(lowered) & DEPENDENCY_DIRS:
        return 'dependency/cache directory'
    if '.git' in lowered:
        return 'nested Git metadata'
    if path in PLACEHOLDERS:
        return None
    if set(lowered) & OUTPUT_DIRS or lowered[0] == 'reports':
        return 'generated execution output'
    pairs = set(zip(lowered, lowered[1:]))
    if pairs & {('api', 'results'), ('api', 'local-state'), ('ui', 'results'), ('ui', 'reports')}:
        return 'execution output/local state'
    if path.startswith('archive/interface-scans/') and path != 'archive/interface-scans/README.md':
        return 'retired raw scan payload'
    if name in RAW_NAMES or name.endswith(('.har', '.log', '.sqlite', '.sqlite3', '.db')):
        return 'raw response/execution state'
    if name.startswith('.env') and name != '.env.example':
        return 'local environment file'
    if name.endswith(('.key', '.pem', '.p12')):
        return 'local credential file'
    if name.endswith(('.zip', '.tar', '.tgz', '.tar.gz', '.7z', '.rar')):
        return 'generated archive; retain its source/packager instead'
    # A reusable runtime may be exported outside this repository, never vendored
    # back under another directory. Original scripts/ remains the single source.
    for offset, component in enumerate(lowered[:-1]):
        if component == 'scripts' and offset > 0:
            tail = lowered[offset + 1:]
            if tail[0] in {'qa_core', 'filbet', 'qa_delivery', 'qa_workflow'} or tail in {
                ('python-launcher.mjs',), ('python-runtime.mjs',), ('run-local.py',),
                ('run-qa.py',), ('run-requirement.py',),
            }:
                return 'nested executor/runtime copy'
    if name == 'runtime-manifest.json':
        return 'exported runtime copy'
    return None


def copied_roots(paths):
    """Detect a nested repository even if its executor files were omitted."""
    paths = set(paths)
    roots = set()
    for path in paths:
        if path.endswith('/package.json'):
            prefix = path[:-len('package.json')]
            if any(prefix + marker in paths for marker in (
                'AGENTS.md', 'api/p0/test-cases.csv', 'config/local-commands.json',
                'scripts/python-launcher.mjs',
            )):
                roots.add(prefix)
    return roots


@dataclass(frozen=True)
class Entry:
    path: str
    oid: str
    size: int
    mode: str = '100644'


@dataclass(frozen=True)
class Policy:
    file_warning_bytes: int = MIB
    file_block_bytes: int = 5 * MIB
    batch_warning_bytes: int = 25 * MIB
    batch_warning_files: int = 500
    exceptions: tuple = ()

    @classmethod
    def parse(cls, data):
        keys = {'version', 'file_warning_bytes', 'file_block_bytes',
                'batch_warning_bytes', 'batch_warning_files', 'source_csv_size_exceptions'}
        if not isinstance(data, dict) or set(data) != keys or data['version'] != 1:
            raise FilePolicyError('Invalid repository file policy schema')
        expected = {'file_warning_bytes': MIB, 'file_block_bytes': 5 * MIB,
                    'batch_warning_bytes': 25 * MIB, 'batch_warning_files': 500}
        if any(type(data[k]) is not int or data[k] != v for k, v in expected.items()):
            raise FilePolicyError('File policy thresholds must remain 1/5/25 MiB and 500 files')
        exceptions = data['source_csv_size_exceptions']
        if not isinstance(exceptions, list):
            raise FilePolicyError('Invalid source CSV size exceptions')
        seen = set()
        for item in exceptions:
            if not isinstance(item, dict) or set(item) != {'path', 'blob_oid', 'bytes', 'reason'}:
                raise FilePolicyError('CSV exception requires path, blob_oid, bytes and reason')
            path = item['path']
            if (not valid_path(path) or not path.startswith(SOURCE_CSV_ROOTS)
                    or not path.endswith('.csv') or forbidden_reason(path)):
                raise FilePolicyError('Size exceptions are limited to reviewed source CSV paths')
            if (not isinstance(item['blob_oid'], str)
                    or not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', item['blob_oid'])
                    or type(item['bytes']) is not int or item['bytes'] <= 5 * MIB
                    or not isinstance(item['reason'], str) or not item['reason'].strip()
                    or path in seen):
                raise FilePolicyError('Invalid or duplicate exact CSV size exception')
            seen.add(path)
        return cls(**expected, exceptions=tuple(exceptions))

    def permits_size(self, entry):
        return any(item['path'] == entry.path and item['blob_oid'] == entry.oid
                   and item['bytes'] == entry.size for item in self.exceptions)


@dataclass
class Report:
    scope: str
    files: int = 0
    versions: int = 0
    bytes: int = 0
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    @property
    def ok(self):
        return not self.errors


def inspect_entries(entries, policy, scope, *, batch=True, paths=()):
    # Changed paths count once; byte totals include each distinct path/blob version
    # so pushing an intermediate large file and then deleting it is still visible.
    unique = {(e.path, e.oid): e for e in entries}
    report = Report(scope, len({e.path for e in unique.values()}), len(unique),
                    sum(e.size for e in unique.values()))
    copies = copied_roots(set(paths) | {e.path for e in unique.values()})
    for entry in sorted(unique.values(), key=lambda e: (e.path, e.oid)):
        label = json.dumps(entry.path, ensure_ascii=True)
        reason = forbidden_reason(entry.path)
        if not reason and any(entry.path.startswith(prefix) for prefix in copies):
            reason = 'nested repository copy'
        if entry.mode == '160000':
            reason = 'uninspected Git submodule; do not vendor dependencies/executors'
        if reason:
            report.errors.append(f'{label}: {reason}')
        if entry.path in PLACEHOLDERS and (
            entry.mode == '120000' or not (entry.size == 0 or entry.size == 1 and entry.oid in NEWLINE_BLOBS)
        ):
            report.errors.append(f'{label}: output placeholder must be empty or exactly one LF in a regular file')
        if entry.size > policy.file_block_bytes:
            if not reason and entry.mode != '120000' and policy.permits_size(entry):
                report.warnings.append(f'{label}: reviewed exact CSV size exception ({entry.size} bytes, {entry.oid})')
            else:
                report.errors.append(f'{label}: {entry.size} bytes exceeds 5 MiB ({entry.oid})')
        elif entry.size >= policy.file_warning_bytes:
            report.warnings.append(f'{label}: {entry.size} bytes reaches 1 MiB ({entry.oid})')
    if batch:
        batch_warnings(report, policy)
    return report


def batch_warnings(report, policy):
    if report.bytes > policy.batch_warning_bytes:
        report.warnings.append(f'Batch {report.bytes} bytes exceeds the 25 MiB target (warning only)')
    if report.files > policy.batch_warning_files:
        report.warnings.append(f'Batch {report.files} changed paths exceeds the 500-file target (warning only)')


class Repository:
    def __init__(self, root):
        self.root = Path(root).resolve()
        # Do not lazily fetch partial-clone objects, acquire optional locks, or
        # allow local replacement refs to hide the actual objects being pushed.
        self.env = {**os.environ, 'GIT_NO_REPLACE_OBJECTS': '1',
                    'GIT_NO_LAZY_FETCH': '1', 'GIT_OPTIONAL_LOCKS': '0'}
        self.object_format = self.git('rev-parse', '--show-object-format').decode().strip()
        if self.object_format not in {'sha1', 'sha256'}:
            raise FilePolicyError('Unsupported Git object format')
        self.oid_length = 40 if self.object_format == 'sha1' else 64
        self._sizes = {}
        self._policies = {}

    def git(self, *args, input=None, acceptable=(0,)):
        result = subprocess.run(['git', '-C', str(self.root), *args], input=input,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env)
        if result.returncode not in acceptable:
            raise FilePolicyError(f'Git {args[0]} failed; scope/object unavailable, refusing a partial check')
        return result.stdout

    def oid(self, value, *, zero=False):
        if (not isinstance(value, str) or not re.fullmatch('[0-9a-f]{' + str(self.oid_length) + '}', value)
                or (not zero and set(value) == {'0'})):
            raise FilePolicyError('Invalid Git object ID in check scope')
        return value

    def commit(self, value):
        self.oid(value)
        commit = self.git('rev-parse', '--verify', '--end-of-options', value + '^{commit}').decode().strip()
        return self.oid(commit)

    def policy(self, *, staged=False, revision=None, allow_missing=False):
        try:
            if staged:
                records = [r for r in self.index() if r[0] == POLICY_PATH]
            elif revision:
                records = [r for r in self.tree_records(self.commit(revision)) if r[0] == POLICY_PATH]
            else:
                path = self.root / POLICY_PATH
                if path.is_symlink() or not path.parent.resolve().is_relative_to(self.root):
                    raise FilePolicyError('Repository file policy must be a local regular file')
                return Policy.parse(json.loads(path.read_text(encoding='utf-8')))
            if not records:
                if allow_missing:
                    # Commits made before the gate existed receive the fixed
                    # strict defaults, never uncommitted or another ref's exceptions.
                    return Policy()
                raise FilePolicyError('Repository file policy is missing from the checked index/commit')
            entry, = self.blobs(records)
            if entry.mode not in {'100644', '100755'} or entry.size > 65536:
                raise FilePolicyError('Repository file policy must be a regular JSON file within 64 KiB')
            if entry.oid not in self._policies:
                data = self.git('cat-file', 'blob', entry.oid).decode('utf-8')
                self._policies[entry.oid] = Policy.parse(json.loads(data))
            return self._policies[entry.oid]
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise FilePolicyError('Repository file policy is missing or unreadable') from exc

    def index(self):
        entries = []
        for record in self.git('ls-files', '--stage', '-z').split(b'\0'):
            if not record:
                continue
            metadata, path = record.split(b'\t', 1)
            mode, oid, stage = metadata.decode('ascii').split()
            if stage != '0':
                raise FilePolicyError('Unmerged index entries; resolve conflicts before checking')
            entries.append((os.fsdecode(path), oid, mode))
        return entries

    def blobs(self, records):
        missing = sorted({oid for _, oid, mode in records if mode != '160000'} - self._sizes.keys())
        if missing:
            output = self.git('cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize)',
                              input=('\n'.join(missing) + '\n').encode('ascii'))
            lines = output.decode('ascii').splitlines()
            if len(lines) != len(missing):
                raise FilePolicyError('Incomplete Git blob metadata')
            for expected, line in zip(missing, lines):
                parts = line.split()
                if len(parts) != 3 or parts[0] != expected or parts[1] != 'blob' or not parts[2].isdigit():
                    raise FilePolicyError('Missing/non-blob Git object; refusing a partial check')
                self._sizes[expected] = int(parts[2])
        return [Entry(path, oid, 0 if mode == '160000' else self._sizes[oid], mode)
                for path, oid, mode in records]

    def worktree(self):
        entries = []
        for path, _, index_mode in self.index():
            if index_mode == '160000':
                entries.append(Entry(path, '', 0, '160000'))
                continue
            target = self.root / path
            if not target.parent.resolve().is_relative_to(self.root):
                raise FilePolicyError('Tracked path traverses a symlink outside the repository')
            try:
                info = target.lstat()
            except FileNotFoundError:
                continue  # unstaged deletion; the staged check still sees the blob
            if stat.S_ISLNK(info.st_mode):
                data = os.fsencode(os.readlink(target))
                size = len(data)
                digest = hashlib.new(self.object_format, f'blob {size}\0'.encode() + data).hexdigest()
                mode = '120000'
            elif stat.S_ISREG(info.st_mode):
                size = info.st_size
                hashed = hashlib.new(self.object_format, f'blob {size}\0'.encode())
                with target.open('rb') as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                        hashed.update(chunk)
                digest, mode = hashed.hexdigest(), '100644'
            else:
                raise FilePolicyError('Tracked path is not a regular file/symlink; inspect it before proceeding')
            entries.append(Entry(path, digest, size, mode))
        return entries

    def check_worktree(self, policy):
        return inspect_entries(self.worktree(), policy, 'tracked worktree', batch=False)

    def check_staged(self):
        policy = self.policy(staged=True)
        index = self.index()
        changed = {os.fsdecode(p) for p in self.git(
            'diff', '--cached', '--name-only', '--no-renames', '--diff-filter=ACMT', '-z').split(b'\0') if p}
        return inspect_entries(self.blobs([r for r in index if r[0] in changed]), policy,
                               'staged Git blobs', paths=[p for p, _, _ in index])

    def full_history_available(self):
        if self.git('rev-parse', '--is-shallow-repository').strip() != b'false':
            raise FilePolicyError('Shallow history cannot establish push scope; fetch full history first')

    def tree_records(self, commit):
        records = []
        for item in self.git('ls-tree', '-r', '-z', commit).split(b'\0'):
            if item:
                metadata, path = item.split(b'\t', 1)
                mode, _, oid = metadata.decode('ascii').split()
                records.append((os.fsdecode(path), oid, mode))
        return records

    def changed_records(self, commit, parent=None):
        if parent is None:
            return self.tree_records(commit)
        raw = self.git('diff-tree', '--no-commit-id', '--raw', '-r', '-z', '--no-renames',
                       '--diff-filter=ACMT', parent, commit).split(b'\0')
        records = []
        for i in range(0, len(raw) - 1, 2):
            metadata, path = raw[i], raw[i + 1]
            if not metadata.startswith(b':'):
                raise FilePolicyError('Unexpected Git tree diff; refusing a partial check')
            _, mode, _, oid, _ = metadata[1:].decode('ascii').split()
            records.append((os.fsdecode(path), oid, mode))
        return records

    def check_commits(self, tips, bases, *, scope='commit range'):
        self.full_history_available()
        tips = sorted({self.commit(tip) for tip in tips})
        bases = sorted({self.commit(base) for base in bases})
        if not tips:
            return inspect_entries([], Policy(), scope)
        args = ['rev-list', '--parents', *tips]
        if bases:
            args.extend(['--not', *bases])
        entries = []
        warnings, errors = [], []
        for row in self.git(*args).decode('ascii').splitlines():
            commit, *parents = row.split()
            changed = self.blobs(self.changed_records(commit, parents[0] if parents else None))
            entries.extend(changed)
            # Check structural copies against each full tree, not only that
            # commit's delta; this catches copies assembled over several commits.
            tree_paths = [p for p, _, _ in self.tree_records(commit)]
            checked = inspect_entries(changed, self.policy(revision=commit, allow_missing=True),
                                      scope, batch=False, paths=tree_paths)
            warnings.extend(checked.warnings)
            errors.extend(checked.errors)
        unique = {(entry.path, entry.oid): entry for entry in entries}
        report = Report(scope, len({entry.path for entry in entries}), len(unique),
                        sum(entry.size for entry in unique.values()),
                        list(dict.fromkeys(warnings)), list(dict.fromkeys(errors)))
        batch_warnings(report, Policy())
        return report

    def remote_bases(self, remote, updates):
        bases = {self.commit(old) for _, _, _, old in updates if set(old) != {'0'}}
        remotes = self.git('remote').decode().splitlines()
        if remote not in remotes:
            return bases
        excluded = {f'refs/remotes/{remote}/' + ref[len('refs/heads/'):]
                    for _, _, ref, _ in updates if ref.startswith('refs/heads/')}
        for row in self.git('for-each-ref', '--format=%(refname) %(objectname)', f'refs/remotes/{remote}/').decode().splitlines():
            ref, oid = row.split()
            if ref not in excluded:
                bases.add(self.commit(oid))
        return bases

    def check_push(self, text, remote):
        updates = []
        for line in text.splitlines():
            columns = line.split()
            if len(columns) != 4:
                raise FilePolicyError('Invalid pre-push input; expected all four fields for each ref')
            local_ref, local, remote_ref, old = columns
            self.oid(local, zero=True)
            self.oid(old, zero=True)
            # Explicit pushes may identify the source as HEAD or a full SHA,
            # rather than refs/heads/...; the validated object ID defines scope.
            if not remote_ref.startswith('refs/'):
                raise FilePolicyError('Invalid ref in pre-push input')
            updates.append((local_ref, local, remote_ref, old))
        active = [u for u in updates if set(u[1]) != {'0'}]
        if not active:
            return inspect_entries([], Policy(), 'push (no new objects)')
        self.full_history_available()
        bases = self.remote_bases(remote, updates)
        tips = []
        for _, local, _, old in active:
            tip = self.commit(local)
            tips.append(tip)
            if set(old) == {'0'}:
                # Never use --all or a local branch as an exclusion: doing so
                # would hide unpublished work on a newly created remote branch.
                connected = [base for base in bases if self.git(
                    'merge-base', tip, base, acceptable=(0, 1)).strip()]
                if not connected:
                    raise FilePolicyError('New remote ref has no known shared remote history; fetch the remote first, or explicitly audit a root range')
        return self.check_commits(tips, bases, scope='push Git blobs (all new commits)')

    def check_ci(self, event_name, event):
        if event_name == 'pull_request':
            try:
                base = event['pull_request']['base']['sha']
                head = event['pull_request']['head']['sha']
            except (KeyError, TypeError) as exc:
                raise FilePolicyError('Missing pull request scope') from exc
            return self.check_commits([head], [base], scope='CI pull request commits')
        if event_name != 'push':
            raise FilePolicyError('Unsupported CI event; refusing an unspecified scope')
        try:
            head, base = self.oid(event['after'], zero=True), self.oid(event['before'], zero=True)
        except (KeyError, TypeError) as exc:
            raise FilePolicyError('Missing CI push scope') from exc
        if set(head) == {'0'}:
            return inspect_entries([], Policy(), 'CI deleted ref')
        if set(base) != {'0'}:
            return self.check_commits([head], [base], scope='CI pushed commits')
        # Checkout already points remote/<new branch> at the new tip. It must
        # never become its own exclusion. Only the other/default branch is a base.
        default = event.get('repository', {}).get('default_branch')
        if not isinstance(default, str) or not default or event.get('ref') == 'refs/heads/' + default:
            raise FilePolicyError('Initial/default-branch CI push needs an explicit audited base/root range')
        ref = 'refs/remotes/origin/' + default
        base = self.git('rev-parse', '--verify', '--end-of-options', ref + '^{commit}').decode().strip()
        if not self.git('merge-base', self.commit(head), self.commit(base), acceptable=(0, 1)).strip():
            raise FilePolicyError('New CI branch has no shared default-branch history')
        return self.check_commits([head], [base], scope='CI new branch commits')


def print_report(report):
    for message in report.errors:
        print('BLOCK:', message)
    for message in report.warnings:
        print('WARN:', message)
    print(f'Repository files {"PASS" if report.ok else "FAIL"}: {report.scope}; '
          f'{report.files} paths, {report.versions} path/blob versions, {report.bytes} bytes; '
          f'{len(report.errors)} blockers, {len(report.warnings)} warnings')


def main(argv=None):
    import argparse
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    sub = parser.add_subparsers(dest='mode', required=True)
    sub.add_parser('repo', help='Current tracked worktree files; no whole-repository batch budget')
    sub.add_parser('staged', help='Added/modified index blobs, never unstaged content')
    push = sub.add_parser('push', help='Read all Git pre-push ref updates from stdin')
    push.add_argument('--remote', required=True)
    revision = sub.add_parser('range', help='Inspect every commit in an explicit offline range')
    revision.add_argument('--head', required=True)
    group = revision.add_mutually_exclusive_group(required=True)
    group.add_argument('--base')
    group.add_argument('--root-history', action='store_true', help='Explicitly audit all reachable history')
    ci = sub.add_parser('ci', help='Use push/PR object IDs from a GitHub event file')
    ci.add_argument('--event-name', default=os.environ.get('GITHUB_EVENT_NAME'))
    ci.add_argument('--event-path', type=Path, default=os.environ.get('GITHUB_EVENT_PATH'))
    args = parser.parse_args(argv)
    try:
        repo = Repository(args.root)
        if args.mode == 'repo':
            report = repo.check_worktree(repo.policy())
        elif args.mode == 'staged':
            report = repo.check_staged()
        elif args.mode == 'push':
            report = repo.check_push(sys.stdin.read(), args.remote)
        elif args.mode == 'range':
            report = repo.check_commits([args.head], [args.base] if args.base else [])
        else:
            if not args.event_path:
                raise FilePolicyError('CI event file is required')
            report = repo.check_ci(args.event_name, json.loads(args.event_path.read_text()))
        print_report(report)
        return 0 if report.ok else 1
    except (FilePolicyError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        message = str(exc) if isinstance(exc, FilePolicyError) else 'Unable to read local Git metadata/policy; refusing a partial check'
        print('Repository files ERROR:', message, file=sys.stderr)
        return 2
