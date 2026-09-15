"""Commit-pinned Bruno discovery and traceable requirement association."""
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile
from qa_delivery.pipeline import redact_value, write_json
from qa_delivery.state import digest


def git(repo, *args):
    return subprocess.run(['git','-C',str(repo),*args], check=True, capture_output=True).stdout


def sync(state, source, ref='HEAD', fetch=False):
    source = Path(source).resolve()
    repo = Path(git(source,'rev-parse','--show-toplevel').decode().strip())
    prefix = source.relative_to(repo).as_posix()
    if prefix == '.': prefix = ''
    if fetch:
        git(repo,'fetch','origin')
        ref = 'origin/main' if ref == 'HEAD' else ref
    commit = git(repo,'rev-parse','--verify',ref+'^{commit}').decode().strip()
    identity = digest([str(repo), prefix])
    previous = state.meta('documents:'+identity)
    before = previous['commit'] if previous else None
    mapping_path = state.root/'config/workflow-documents.json'
    mappings = json.loads(mapping_path.read_text(encoding='utf-8')).get('mappings',[]) if mapping_path.is_file() else []
    if before == commit and previous.get('mapping_sha256') == digest(mappings):
        return {**previous, 'unchanged': True}
    if before == commit:
        before = previous.get('previous_commit')
    if before:
        # Rewritten history is not a normal incremental update.
        git(repo,'merge-base','--is-ancestor',before,commit)
        changed = git(repo,'diff','--name-only','-z',before,commit,'--',prefix or '.').decode().split('\0')
    else:
        changed = git(repo,'ls-tree','-r','--name-only','-z',commit,'--',prefix or '.').decode().split('\0')
    changed = [name for name in changed if name.endswith('.bru')]
    spec = importlib.util.spec_from_file_location('workflow_bruno',state.root/'scripts/scan-bruno-interfaces.py')
    scanner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scanner)
    # Read a committed archive, never checkout/reset the user's document repository.
    archive = git(repo,'archive','--format=zip',commit, '--', prefix or '.')
    texts = {}
    with tempfile.TemporaryDirectory(prefix='qa-documents-') as tmp:
        base = Path(tmp)
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            for item in bundle.infolist():
                if not item.filename.endswith('.bru'): continue
                dest = base/item.filename
                if not dest.resolve().is_relative_to(base.resolve()): raise ValueError('invalid archive path')
                dest.parent.mkdir(parents=True, exist_ok=True)
                data = bundle.read(item)
                dest.write_bytes(data)
                if item.filename in changed: texts[item.filename] = data.decode('utf-8-sig',errors='replace')
        collection = base/prefix if prefix else base
        rows = scanner.collect_rows(collection)
        scanner.write_csv(rows,state.root/'api/inventory/interfaces.csv')
        scanner.write_markdown(rows,source,state.root/'api/inventory/interfaces.csv',state.root/'api/inventory/interfaces.md')
    subprocess.run([sys.executable, 'scripts/build-api-catalog.py'], cwd=state.root, check=True, capture_output=True)
    evidence = {}
    for seed in state.seed():
        directory = state.root/'requirements'/seed['story']
        evidence[seed['story']] = '\n'.join(p.read_text(encoding='utf-8') for p in
            (directory/'design.md',directory/'test-cases.md',directory/'api/contract-review.md') if p.is_file())
    changes = []
    for name in changed:
        content = texts.get(name,'')
        method, url = scanner.extract_request(content)
        route = scanner.normalize_path(url) if url else ''
        associations = []
        for story, requirement in evidence.items():
            explicit = story in name or story in content
            matched = bool(route and route != '/' and route in requirement)
            if explicit or matched:
                associations.append({'story':story,'basis':'文档明确需求编号' if explicit else '需求资料引用同一路径（关联推断，非部署证据）'})
        local_name = name[len(prefix)+1:] if prefix else name
        for mapping in mappings:
            if local_name.startswith(mapping['prefix']) and mapping['story'] in evidence and not any(a['story']==mapping['story'] for a in associations):
                associations.append({'story':mapping['story'],'basis':mapping['basis']})
        changes.append({'file': name, 'change': 'modified_or_added' if content else 'deleted',
            'method':method,'path':route,'content_sha256':digest(content), 'requirements':associations})
    result = {'commit':commit, 'previous_commit':before, 'source':str(source), 'changes':changes,
              'baseline': before is None, 'mapping_sha256':digest(mappings), 'unmatched':[c['file'] for c in changes if not c['requirements']],
              'note':'首次建立基线不冒充本次增量；文档更新不是提测或部署证明'}
    folder = state.directory/'documents'/(commit+'-'+digest(mappings)[:12])
    folder.mkdir(parents=True, exist_ok=True)
    write_json(folder/'changes.json',redact_value(result))
    for story in evidence:
        related = [c for c in changes if any(a['story']==story for a in c['requirements'])]
        if related:
            state.append(story,'documents',{'status':'接口文档待评估','commit':commit,'previous_commit':before,
                'changes':related,'source':str((folder/'changes.json').relative_to(state.root)) if folder.is_relative_to(state.root) else str(folder/'changes.json')})
    state.meta('documents:'+identity, result)
    return result
