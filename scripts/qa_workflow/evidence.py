"""Offline review-baseline checks. Hash agreement is not semantic or business approval."""
import hashlib
import json
import re
from pathlib import Path

from qa_core.case_catalogue import design_rows


def file_hash(path):
    # Normalize line endings so a Windows checkout does not invalidate a review.
    return hashlib.sha256(Path(path).read_text(encoding='utf-8-sig').encode('utf-8')).hexdigest()


def review(root, story):
    if not re.fullmatch(r'ISOP-\d+', story):
        raise ValueError('invalid requirement')
    folder = Path(root) / 'requirements' / story
    manifest = folder / 'evidence-sync.json'
    result = {'story': story, 'status': 'UNREVIEWED', 'errors': [], 'pending': []}
    if not folder.is_dir():
        result.update(status='INVALID', errors=['需求目录不存在'])
        return result
    if not manifest.is_file():
        result['pending'].append('尚未登记证据同步基线；不代表来源没有更新')
        return result
    try:
        data = json.loads(manifest.read_text(encoding='utf-8'))
        if data.get('schema_version') != 1 or data.get('story') != story:
            raise ValueError('证据基线版本或需求编号错误')
        if not data.get('reviewed_at') or not data.get('reviewer'):
            raise ValueError('缺少复核时间或复核人')
        files = data['files']
        required = {'design.md', 'questions.md', 'test-cases.md', 'cases.csv', 'evidence-sync.md'}
        required.update(name for name in ('plan.json', 'api/cases.json', 'api/data-cases.csv', 'api/contract-review.md')
                        if (folder / name).is_file())
        if not required <= files.keys():
            raise ValueError('同步基线遗漏现有设计、执行源或生成视图')
        for name, expected in files.items():
            path = (folder / name).resolve()
            if not path.is_relative_to(folder.resolve()) or name == 'evidence-sync.json':
                raise ValueError('证据路径必须在需求目录内且不能引用自身')
            if not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected):
                raise ValueError('无效文件hash')
            if not path.is_file() or file_hash(path) != expected:
                result['errors'].append(f'{name} 已变化或缺失，需复核影响后更新基线')
        sources = data['sources']
        ids = [s['id'] for s in sources]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError('来源编号为空或重复')
        for source in sources:
            if not source.get('locator') or not source.get('coverage'):
                raise ValueError('来源缺定位或读取范围')
            if source['status'] not in ('READ', 'PENDING'):
                raise ValueError('无效来源状态')
            if source['status'] == 'READ' and (not source.get('checked_at') or not source.get('revision')):
                raise ValueError('已读来源必须记录读取时间与版本')
            if source['status'] == 'PENDING':
                result['pending'].append(source['id'] + '：' + source['coverage'])
        known = {r['Case ID'] for r in design_rows(folder / 'test-cases.md', story)}
        changes = data['changes']
        if not changes or len({c['id'] for c in changes}) != len(changes):
            raise ValueError('变更编号为空或重复')
        for change in changes:
            if not change['source_ids'] or not set(change['source_ids']) <= set(ids):
                raise ValueError('变更引用未知来源')
            if not change['case_ids'] or not set(change['case_ids']) <= known:
                raise ValueError('变更引用未知用例')
            if change['status'] not in ('SYNCED', 'PENDING') or not change.get('action') or not change.get('verification'):
                raise ValueError('变更缺少同步动作或实测边界')
            if change['status'] == 'PENDING':
                result['pending'].append(change['id'] + '：' + change['action'])
        result['status'] = 'STALE' if result['errors'] else 'PARTIAL' if result['pending'] else 'REVIEWED'
    except (ValueError, KeyError, TypeError, AttributeError, OSError) as error:
        result['status'] = 'INVALID'
        result['errors'].append('证据基线无效：' + str(error))
    return result


def check_all(root, story=None):
    stories = [story] if story else sorted(p.name for p in (Path(root) / 'requirements').glob('ISOP-*') if p.is_dir())
    return [review(root, name) for name in stories]
