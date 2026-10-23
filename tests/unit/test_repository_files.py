"""Real temporary Git repositories exercise index/push boundaries without a remote service."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from support import ROOT
from qa_core.repository_files import (
    Entry, FilePolicyError, MIB, NEWLINE_BLOBS, Policy, Repository, forbidden_reason,
    inspect_entries, main,
)


class FilePolicyTests(unittest.TestCase):
    def test_file_thresholds_and_batch_targets_are_exact(self):
        policy = Policy()
        for size, warn, block in [(MIB - 1, False, False), (MIB, True, False),
                                  (5 * MIB, True, False), (5 * MIB + 1, False, True)]:
            report = inspect_entries([Entry('design.txt', 'a' * 40, size)], policy, 'test')
            self.assertEqual(bool(report.warnings), warn)
            self.assertEqual(bool(report.errors), block)
        at_target = [Entry(f'{i}.txt', str(i), 5 * MIB) for i in range(5)]
        self.assertFalse(any('Batch' in w for w in inspect_entries(at_target, policy, 'test').warnings))
        over = inspect_entries(at_target + [Entry('extra.txt', 'b' * 40, 1)], policy, 'test')
        self.assertTrue(over.ok)
        self.assertTrue(any('25 MiB' in w for w in over.warnings))
        paths = [Entry(f'{i}.txt', str(i), 1) for i in range(501)]
        self.assertFalse(inspect_entries(paths[:500], policy, 'test').warnings)
        self.assertTrue(inspect_entries(paths, policy, 'test').ok)
        self.assertTrue(any('500-file' in w for w in inspect_entries(paths, policy, 'test').warnings))
        self.assertFalse(inspect_entries(paths, policy, 'whole repo', batch=False).warnings)

    def test_forbidden_categories_do_not_ban_design_history_or_xmind(self):
        bad = ['node_modules/a.js', 'nested/.venv/a.py', 'reports/a.json',
               'requirements/history/old/api/results/result.csv', 'tmp/raw-responses/a.csv',
               'archive/interface-scans/old/data.json', 'tmp/result.json', 'capture.har',
               'copy/scripts/qa_core/process.py', 'copy/scripts/run-local.py',
               'copy/runtime-manifest.json', 'copy.zip', '.env.fat']
        for path in bad:
            with self.subTest(path=path):
                self.assertIsNotNone(forbidden_reason(path))
        good = ['requirements/history/old/plan.json', 'requirements/history/old/cases.csv',
                'requirements/ISOP-2124/ISOP-2124-测试用例.xmind',
                'api/inventory/interfaces.csv', 'archive/interface-scans/README.md',
                'scripts/qa_core/process.py', '.env.example']
        for path in good:
            with self.subTest(path=path):
                self.assertIsNone(forbidden_reason(path))
        for size, mode in [(1, '100644'), (0, '120000')]:
            self.assertFalse(inspect_entries([Entry('api/results/.gitkeep', 'a', size, mode)], Policy(), 'test').ok)
        self.assertTrue(inspect_entries([Entry('api/results/.gitkeep', next(iter(NEWLINE_BLOBS)), 1)], Policy(), 'test').ok)

    def test_exact_source_csv_exception_cannot_exempt_other_files_or_categories(self):
        data = json.loads((ROOT / 'config/repository-file-policy.json').read_text())
        exception = {'path': 'api/inventory/large.csv', 'blob_oid': 'a' * 40,
                     'bytes': 6 * MIB, 'reason': 'Reviewed source inventory required by the builder'}
        data['source_csv_size_exceptions'] = [exception]
        policy = Policy.parse(data)
        permitted = inspect_entries([Entry(exception['path'], 'a' * 40, 6 * MIB)], policy, 'test')
        self.assertTrue(permitted.ok)
        self.assertTrue(any('exception' in w for w in permitted.warnings))
        for entry in [Entry(exception['path'], 'b' * 40, 6 * MIB),
                      Entry(exception['path'], 'a' * 40, 6 * MIB + 1),
                      Entry('api/inventory/other.csv', 'a' * 40, 6 * MIB)]:
            self.assertFalse(inspect_entries([entry], policy, 'test').ok)
        for path in ['api/results/raw.csv', 'api/inventory/node_modules/raw.csv',
                     'requirements/ISOP-1/cases.csv', 'api/inventory/large.json']:
            data['source_csv_size_exceptions'] = [{**exception, 'path': path}]
            with self.assertRaises(FilePolicyError):
                Policy.parse(data)
        data['source_csv_size_exceptions'] = [exception]
        data['file_block_bytes'] = 100 * MIB
        with self.assertRaises(FilePolicyError):
            Policy.parse(data)

    def test_copy_fingerprint_uses_complete_snapshot_and_paths_are_escaped(self):
        report = inspect_entries([Entry('backup/package.json', 'a', 1)], Policy(), 'test',
                                 paths=['backup/AGENTS.md', 'backup/package.json'])
        self.assertFalse(report.ok)
        label = 'raw-responses/odd\n name.json'
        report = inspect_entries([Entry(label, 'a', 1)], Policy(), 'test')
        self.assertIn('\\n', report.errors[0])
        self.assertNotIn('\n', report.errors[0])


class RepositoryFilesGitTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / 'repo with spaces'
        self.root.mkdir()
        # Hooks may run these tests while exporting GIT_INDEX_FILE/GIT_DIR. Do
        # not let test Git writes touch the caller's repository/index.
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        self.env.update({'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
                         'GIT_AUTHOR_NAME': 'Offline test', 'GIT_AUTHOR_EMAIL': 'test@example.invalid',
                         'GIT_COMMITTER_NAME': 'Offline test', 'GIT_COMMITTER_EMAIL': 'test@example.invalid'})
        environment = patch.dict(os.environ, self.env, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        self.git('init', '--quiet')
        self.git('config', 'core.hooksPath', os.devnull)
        self.git('config', 'core.autocrlf', 'false')
        self.write('readme.txt', b'initial\n')
        self.write('config/repository-file-policy.json', (ROOT / 'config/repository-file-policy.json').read_bytes())
        self.git('add', 'readme.txt', 'config')
        self.base = self.commit()
        self.repo = Repository(self.root)
        self.repo.env = {**self.env, 'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_NO_LAZY_FETCH': '1', 'GIT_OPTIONAL_LOCKS': '0'}
        self.policy = Policy()
        self.zero = '0' * 40

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], env=self.env, stderr=subprocess.PIPE).decode().strip()

    def write(self, path, data):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def commit(self):
        self.git('commit', '--quiet', '-m', 'offline fixture')
        return self.git('rev-parse', 'HEAD')

    def remote(self, oid=None):
        self.git('remote', 'add', 'origin', str(self.root.parent / 'unused-remote'))
        self.git('update-ref', 'refs/remotes/origin/main', oid or self.base)

    def push_row(self, head, old=None, branch='feature', source='refs/heads/feature'):
        return f'{source} {head} refs/heads/{branch} {old or self.zero}\n'

    def test_staged_uses_index_not_unstaged_content_and_handles_unborn_head(self):
        self.write('large.txt', b'x' * (5 * MIB + 1))
        self.git('add', 'large.txt')
        self.write('large.txt', b'now small')
        self.assertFalse(self.repo.check_staged().ok)
        self.assertTrue(self.repo.check_worktree(self.policy).ok)
        self.git('add', 'large.txt')
        self.write('large.txt', b'x' * (5 * MIB + 1))
        self.assertTrue(self.repo.check_staged().ok)
        self.assertFalse(self.repo.check_worktree(self.policy).ok)
        self.git('checkout', '--orphan', 'newroot')
        self.assertGreater(self.repo.check_staged().files, 0)

    def test_index_bytes_follow_git_attributes_and_rename_deletion_are_counted_once(self):
        self.write('.gitattributes', b'*.csv text eol=crlf\n')
        self.write('a.csv', b'a,b\r\n1,2\r\n')
        self.git('add', '.gitattributes', 'a.csv')
        self.commit()
        destination = 'with space.csv' if os.name == 'nt' else 'with space\nand newline.csv'
        self.git('mv', 'a.csv', destination)
        result = self.repo.check_staged()
        self.assertTrue(result.ok)
        self.assertEqual(result.files, 1)
        self.assertEqual(result.bytes, len(b'a,b\n1,2\n'))
        self.git('rm', '-f', destination)
        self.assertEqual(self.repo.check_staged().files, 0)

    def large_csv_exception(self):
        path = 'api/inventory/large.csv'
        self.write(path, b'x' * (5 * MIB + 1))
        self.git('add', path)
        data = json.loads((self.root / 'config/repository-file-policy.json').read_text())
        data['source_csv_size_exceptions'] = [{
            'path': path, 'blob_oid': self.git('rev-parse', ':' + path),
            'bytes': 5 * MIB + 1, 'reason': 'Reviewed source fixture for offline tests',
        }]
        return data

    def test_staged_exception_must_be_in_the_index_and_missing_policy_fails_closed(self):
        approved = self.large_csv_exception()
        self.write('config/repository-file-policy.json', json.dumps(approved).encode())
        self.assertFalse(self.repo.check_staged().ok)  # only the CSV is staged
        self.git('add', 'config/repository-file-policy.json')
        self.assertTrue(self.repo.check_staged().ok)
        self.write('config/repository-file-policy.json', (ROOT / 'config/repository-file-policy.json').read_bytes())
        self.assertTrue(self.repo.check_staged().ok)  # worktree must not replace index policy
        self.git('rm', '-f', 'config/repository-file-policy.json')
        with self.assertRaises(FilePolicyError):
            self.repo.check_staged()

    def test_push_ignores_uncommitted_and_later_exceptions(self):
        approved = self.large_csv_exception()
        bad = self.commit()  # committed without a matching policy exception
        self.write('config/repository-file-policy.json', json.dumps(approved).encode())
        self.assertFalse(self.repo.check_push(self.push_row(bad, self.base), 'origin').ok)
        self.assertFalse(self.repo.check_ci('push', {'before': self.base, 'after': bad}).ok)
        self.git('add', 'config/repository-file-policy.json')
        later = self.commit()
        self.assertFalse(self.repo.check_commits([later], [self.base]).ok)
        # An older commit without any policy gets strict defaults, never the
        # later tip's exception or the current uncommitted worktree policy.
        self.git('checkout', '-b', 'before-policy', self.base)
        self.git('rm', 'config/repository-file-policy.json')
        no_policy = self.commit()
        self.write('api/inventory/large.csv', b'x' * (5 * MIB + 1))
        self.git('add', 'api/inventory/large.csv')
        old_style = self.commit()
        self.assertFalse(self.repo.check_commits([old_style], [no_policy]).ok)

    def test_multiple_refs_use_each_commits_own_policy(self):
        approved = self.large_csv_exception()
        bad = self.commit()
        self.git('checkout', '-b', 'approved', self.base)
        self.write('api/inventory/large.csv', b'x' * (5 * MIB + 1))
        self.write('config/repository-file-policy.json', json.dumps(approved).encode())
        self.git('add', 'api/inventory/large.csv', 'config/repository-file-policy.json')
        good = self.commit()
        self.assertTrue(self.repo.check_commits([good], [self.base]).ok)
        self.assertFalse(self.repo.check_commits([bad, good], [self.base]).ok)

    def test_symlink_is_not_followed_and_submodule_is_rejected(self):
        external = self.root.parent / 'external'
        external.write_bytes(b'x' * (6 * MIB))
        try:
            (self.root / 'pointer').symlink_to(external)
        except OSError:
            self.skipTest('symlink creation unavailable')
        self.git('add', 'pointer')
        self.assertTrue(self.repo.check_staged().ok)
        self.assertTrue(self.repo.check_worktree(self.policy).ok)
        self.git('update-index', '--add', '--cacheinfo', '160000,' + self.base + ',submodule')
        self.assertFalse(self.repo.check_staged().ok)
        self.assertFalse(self.repo.check_worktree(self.policy).ok)

    def test_push_and_range_detect_intermediate_large_file_even_after_deletion(self):
        self.write('temporary.bin', b'x' * (5 * MIB + 1))
        self.git('add', 'temporary.bin')
        self.commit()
        self.git('rm', 'temporary.bin')
        head = self.commit()
        self.assertTrue(self.repo.check_worktree(self.policy).ok)
        self.assertFalse(self.repo.check_commits([head], [self.base]).ok)
        self.assertFalse(self.repo.check_push(self.push_row(head, self.base), 'origin').ok)

    def test_old_retired_raw_history_does_not_block_new_commits(self):
        self.write('archive/interface-scans/old/raw.json', b'{}')
        self.git('add', 'archive')
        self.commit()
        self.git('rm', '-r', 'archive')
        cleaned = self.commit()
        self.write('readme.txt', b'new\n')
        self.git('add', 'readme.txt')
        head = self.commit()
        self.assertTrue(self.repo.check_commits([head], [cleaned]).ok)
        self.assertFalse(self.repo.check_commits([head], []).ok)

    def test_new_branch_checks_unpublished_commits_not_all_local_refs(self):
        self.remote()
        self.write('raw-responses/capture.json', b'{}')
        self.git('add', 'raw-responses')
        head = self.commit()
        self.git('branch', 'also-local', head)
        self.assertFalse(self.repo.check_push(self.push_row(head), 'origin').ok)
        self.assertFalse(self.repo.check_push(self.push_row(head, source='HEAD'), 'origin').ok)

    def test_new_branch_missing_remote_baseline_and_unknown_objects_fail_closed(self):
        with self.assertRaises(FilePolicyError):
            self.repo.check_push(self.push_row(self.base), 'origin')
        with self.assertRaises(FilePolicyError):
            self.repo.check_push(self.push_row(self.base, 'f' * 40), 'origin')
        with self.assertRaises(FilePolicyError):
            self.repo.check_push(self.push_row('f' * 40, self.base), 'origin')
        with self.assertRaises(FilePolicyError):
            self.repo.check_push('truncated update', 'origin')

    def test_multiple_refs_noop_deletion_and_annotated_tags(self):
        self.remote()
        self.write('node_modules/dep.js', b'x')
        self.git('add', 'node_modules')
        head = self.commit()
        self.git('tag', '-a', 'review', '-m', 'offline tag')
        tag = self.git('rev-parse', 'review')
        rows = self.push_row(self.base, self.base, 'main') + self.push_row(head) + self.push_row(tag, branch='tag')
        result = self.repo.check_push(rows, 'origin')
        self.assertFalse(result.ok)
        self.assertEqual(result.files, 1)
        self.assertTrue(self.repo.check_push('', 'origin').ok)
        deletion = self.push_row(self.zero, 'f' * 40)
        self.assertTrue(self.repo.check_push(deletion, 'origin').ok)
        self.assertEqual(self.repo.check_push(self.push_row(self.base, self.base), 'origin').files, 0)

    def test_merge_introductions_are_checked_even_if_source_commit_was_remote(self):
        self.git('checkout', '-b', 'side')
        self.write('copy/scripts/python-launcher.mjs', b'copied')
        self.git('add', 'copy')
        side = self.commit()
        self.git('checkout', '-b', 'target', self.base)
        self.write('readme.txt', b'target\n')
        self.git('add', 'readme.txt')
        target = self.commit()
        self.git('merge', '--no-ff', '--no-edit', 'side')
        head = self.git('rev-parse', 'HEAD')
        self.assertFalse(self.repo.check_commits([head], [target, side]).ok)

    def test_copy_assembled_across_commits_is_detected(self):
        self.write('copy/AGENTS.md', b'fixture')
        self.git('add', 'copy')
        base = self.commit()
        self.write('copy/package.json', b'{}')
        self.git('add', 'copy')
        head = self.commit()
        self.assertFalse(self.repo.check_commits([head], [base]).ok)

    def test_shallow_history_is_rejected_without_changing_staged_check(self):
        (self.root / '.git/shallow').write_text(self.base + '\n')
        with self.assertRaises(FilePolicyError):
            self.repo.check_commits([self.base], [])
        self.assertTrue(self.repo.check_staged().ok)

    def test_ci_checks_new_branch_against_default_not_its_own_tracking_ref(self):
        self.remote()
        self.write('reports/response.json', b'{}')
        self.git('add', 'reports')
        head = self.commit()
        self.git('update-ref', 'refs/remotes/origin/feature', head)
        event = {'before': self.zero, 'after': head, 'ref': 'refs/heads/feature',
                 'repository': {'default_branch': 'main'}}
        self.assertFalse(self.repo.check_ci('push', event).ok)
        self.assertFalse(self.repo.check_ci('push', {**event, 'before': self.base}).ok)
        self.assertFalse(self.repo.check_ci('pull_request', {'pull_request': {
            'base': {'sha': self.base}, 'head': {'sha': head}}}).ok)
        with self.assertRaises(FilePolicyError):
            self.repo.check_ci('push', {**event, 'ref': 'refs/heads/main'})
        with self.assertRaises(FilePolicyError):
            self.repo.check_ci('schedule', {})

    def test_cli_missing_policy_fails_closed_and_never_prints_payload(self):
        (self.root / 'config/repository-file-policy.json').unlink()
        error = io.StringIO()
        with redirect_stderr(error):
            self.assertEqual(main(['--root', str(self.root), 'repo']), 2)
        self.write('config/repository-file-policy.json', (ROOT / 'config/repository-file-policy.json').read_bytes())
        self.git('add', 'config')
        self.write('raw-responses/data.json', b'SENSITIVE_TEST_MARKER_DO_NOT_PRINT')
        self.git('add', 'raw-responses')
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(['--root', str(self.root), 'staged']), 1)
        self.assertNotIn('SENSITIVE_TEST_MARKER_DO_NOT_PRINT', output.getvalue())


if __name__ == '__main__':
    unittest.main()
