"""Bind a confirmed task to unified API execution and a frozen manual packet."""
import hashlib
import json
from pathlib import Path
import sys
import uuid
from qa_core.execution_plan import load
from qa_core.team_delivery import prepare, mode, merge_auto, import_results
from filbet.requirement_adapter import METHODS


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def task_plan(root, config, payload):
    """Offline preview, also re-evaluated immediately before execution."""
    path = root/'requirements'/payload['story']/'plan.json'
    if not path.is_file():
        return None
    plan, cases, checksum = load(path, METHODS)
    options = config['stories'][payload['story']].get('execution', {})
    chosen = options.get('case_ids')
    if chosen is not None and (not chosen or len(set(chosen))!=len(chosen) or not set(chosen)<={c['id'] for c in cases}):
        raise ValueError('configured execution case IDs do not match plan')
    cases = [c for c in cases if (chosen is None or c['id'] in chosen) and
             ('ui' in payload['scopes'] if mode(c)=='manual' else 'api' in payload['scopes'])]
    allowed = options.get('allow_write', [])
    automatic, manual, blocked = [], [], {}
    required = set()
    for case in cases:
        if mode(case)=='manual':
            manual.append(case['id'])
            continue
        scopes = set()
        ui = False
        for step in case.get('steps',[]):
            if step['action']=='ui':
                ui = True
            else:
                scope = plan['contracts'][step['contract']].get('scope') if step['action']=='api' else METHODS[step['method']]['scope']
                if scope: scopes.add(scope)
        required.update(scopes)
        if ui or case['review']['类型']=='UI':
            blocked[case['id']] = '新需求UI须人工执行；补充delivery人工说明后重新准备'
        elif scopes-set(allowed):
            blocked[case['id']] = '本批未开放写入范围：'+','.join(sorted(scopes-set(allowed)))
        elif not case.get('steps'):
            blocked[case['id']] = case.get('blocked','执行步骤尚未实现')
        else:
            automatic.append(case['id'])
    return {'runner':'unified','plan_sha256':checksum,'case_ids':[c['id'] for c in cases],
            'automatic_ids':automatic,'manual_ids':manual,'blocked':blocked,
            'allow_write':allowed,'required_write_scopes':sorted(required),
            'insecure':options.get('insecure',False)}


def case_refs(case, story):
    return [r.strip() if r.strip().startswith((story+'-','R')) else story+'-'+r.strip()
            for r in case['review']['验收点'].split(',') if r.strip()]


def review_results(manifest, recorded, evidence):
    by_id = {r['id']:r for r in recorded}
    results = []
    for case in manifest['cases']:
        item = by_id.get(case['id'], {'status':'NOT_RUN','actual':'尚未执行'})
        manual = mode(case)=='manual'
        results.append({'id':('UI:' if manual else 'API:')+case['id'],
            'case_ids':case_refs(case,manifest['requirement']), 'status':item['status'],
            'detail':item.get('actual',''), 'execution_method':'manual' if manual else 'automatic',
            'observation':item, 'evidence':[evidence] if item['status']!='NOT_RUN' else []})
    return results


def run_unified(root, config, payload, folder, command):
    selection = task_plan(root,config,payload)
    if not selection or selection != payload.get('execution'):
        raise ValueError('execution plan/scope changed or not confirmed; scan and confirm again')
    if payload['environment']!='FAT':
        raise ValueError('unified business adapter currently supports FAT only')
    plan,cases,checksum = load(root/'requirements'/payload['story']/'plan.json',METHODS)
    if checksum!=selection['plan_sha256']:
        raise ValueError('execution plan changed while preparing the confirmed task')
    cases = [c for c in cases if c['id'] in selection['case_ids']]
    packet = folder/'team-packet'
    manifest = prepare(plan,cases,checksum,packet,payload['environment'],payload['build'])
    if payload['story']=='ISOP-2027' and selection['manual_ids']:
        from filbet.requirement_kyc import png_bytes
        (packet/'samples').mkdir()
        for size in (256,512000,512001):
            (packet/'samples'/f'{size}.png').write_bytes(png_bytes(size))
    context = {'packet':str(packet.resolve()),'packet_sha256':sha(packet/'packet.json'),
               'auto_paths':[],'auto_sha256':{},'selection':selection}
    write(folder/'workflow.json',context)
    recorded = [{'id':key,'status':'NOT_RUN','actual':reason} for key,reason in selection['blocked'].items()]
    if selection['automatic_ids']:
        index = folder/'api-result-index.json'
        env = config['environments'][payload['environment']]
        argv = [sys.executable,'scripts/run-requirement.py',payload['story'],'--execute',
                '--env',env['env_file'],'--version',payload['build'],
                '--expected-plan-sha256',checksum,'--result-index',str(index.resolve()),
                '--only',*selection['automatic_ids']]
        for scope in selection['allow_write']: argv.extend(['--allow-write',scope])
        if selection['insecure']: argv.append('--insecure')
        code = command(argv,folder,'api',config.get('test_timeout_seconds',900))
        if not index.is_file():
            raise ValueError('API stopped without a complete current result; inspect api.log, never replay writes automatically')
        pointer = json.loads(index.read_text())
        raw = Path(pointer['raw']).resolve()
        base = (root/'reports/qa'/payload['story']).resolve()
        if raw.parent.parent!=base or raw.name!='result.json':
            raise ValueError('API result index is outside the Story result directory')
        report = json.loads(raw.read_text())
        if report.get('cases_sha256')!=checksum or report.get('run_id')!=pointer['run_id'] or report.get('deployment')!=payload['build']:
            raise ValueError('API result does not match confirmed plan/version/run')
        if len(report['results'])!=len(selection['automatic_ids']) or {r['id'] for r in report['results']}!=set(selection['automatic_ids']):
            raise ValueError('API result scope mismatch')
        expected_code = 1 if any(r['status'] in {'FAIL','ERROR'} for r in report['results']) else 2 if any(r['status']=='NOT_RUN' for r in report['results']) else 0
        if code!=expected_code: raise ValueError('API process/report mismatch')
        accepted,_ = merge_auto(manifest,[raw])
        recorded.extend(accepted)
        context['auto_paths'] = [str(raw)]
        context['auto_sha256'] = {str(raw):sha(raw)}
        write(folder/'workflow.json',context)
    write(folder/'api.json',{'results':recorded,'sources':context['auto_paths']})
    return review_results(manifest,recorded,'api.json')


def import_manual(folder, filled, report):
    """Only frozen evidence is imported. No business execution or external writes."""
    if sha(folder/'workflow.json')!=report.get('workflow_sha256'):
        raise ValueError('job evidence manifest changed')
    context = json.loads((folder/'workflow.json').read_text())
    packet = Path(context['packet'])
    if sha(packet/'packet.json')!=context['packet_sha256']:
        raise ValueError('job packet changed')
    if any(sha(p)!=expected for p,expected in context['auto_sha256'].items()):
        raise ValueError('job automatic evidence changed')
    target = folder/('manual-review-'+uuid.uuid4().hex[:8])
    merged = import_results(packet,filled,target,context['auto_paths'])
    manifest = json.loads((packet/'packet.json').read_text())
    incoming = review_results(manifest,merged['results'],str(target.relative_to(folder)/'result.json'))
    # A manual import cannot clear a stopped stage or turn unavailable API items into PASS.
    originals = {r['id']:r for r in report['results']}
    incoming = [r if r['execution_method']=='manual' else originals.get(r['id'],r) for r in incoming]
    incoming.extend(r for r in report['results'] if r['id'] not in {i['id'] for i in incoming})
    return incoming,target
