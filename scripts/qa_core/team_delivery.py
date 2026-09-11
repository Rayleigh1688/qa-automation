"""Offline team packets and audited manual-result import; never executes business steps."""
import copy
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
import uuid
from qa_core.case_report import FIELDS, STATUSES, csv_text, join_results, write_views
from qa_core.execution_plan import expand

class DeliveryError(ValueError):
    """Safe structural diagnosis; never includes filled personal values."""


EDITABLE = ['执行状态','实际结果','证据','执行人','执行时间','未执行原因']
MANUAL_FIELDS = FIELDS + ['执行方式','批次','环境','版本'] + EDITABLE


def validate_delivery(case):
    delivery = case.get('delivery')
    if delivery is None: return
    if delivery.get('mode') not in {'automatic','manual'}:
        raise DeliveryError('unknown delivery mode: '+case['id'])
    if delivery['mode']=='manual':
        for key in ['precondition','steps','expected']:
            if not isinstance(delivery.get(key),str) or not delivery[key].strip():
                raise DeliveryError('manual case needs human-readable '+key)
        if '${' in ''.join(delivery[key] for key in ['precondition','steps','expected']):
            raise DeliveryError('manual instructions cannot expose unresolved runtime variables')


def mode(case):
    return case.get('delivery',{}).get('mode','automatic')


def select_automatic(cases):
    return [c for c in cases if mode(c)=='automatic']


def manual_review(case):
    d = case['delivery']
    return {**case['review'],'前置条件':d['precondition'],'参数/步骤':d['steps'],'预期结果':d['expected']}


def read_csv(path, fields):
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != fields: raise DeliveryError('CSV columns changed')
        rows = list(reader)
    if any(set(r)!=set(fields) or any(v is None for v in r.values()) for r in rows):
        raise DeliveryError('malformed CSV row')
    return rows


def prepare(plan, cases, digest, folder, environment, version, *, extra_views=False):
    if not environment.strip() or not version.strip(): raise DeliveryError('environment/version required')
    for case in cases: validate_delivery(case)
    folder = Path(folder)
    if folder.exists(): raise DeliveryError('use a new packet directory')
    packet_id = 'team-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
    manual = []
    for case in cases:
        if mode(case)!='manual': continue
        manual.append({**manual_review(case),'执行方式':'手动','批次':packet_id,'环境':environment,'版本':version,
            **dict.fromkeys(EDITABLE,''),'执行状态':'NOT_RUN','未执行原因':'待人工执行'})
    source_cases = {c['id']:c for c in expand(plan)}
    if not cases or len({c['id'] for c in cases})!=len(cases) or any(source_cases.get(c['id'])!=c for c in cases):
        raise DeliveryError('packet selection must match the plan')
    # Store the actual escaped cells expected on import (e.g. spreadsheet formula guards).
    encoded = csv_text(manual,MANUAL_FIELDS)
    import io
    frozen = list(csv.DictReader(io.StringIO(encoded.lstrip('\ufeff'))))
    snapshot_text = json.dumps(plan,ensure_ascii=False,indent=2)+'\n'
    manifest = {'plan_snapshot_sha256':hashlib.sha256(snapshot_text.encode()).hexdigest(),'schema_version':1,'packet_id':packet_id,'requirement':plan['requirement'],
        'cases_sha256':digest,'environment':environment,'deployment':version,'cases':cases,'manual_rows':frozen,
        'selected_case_ids':[c['id'] for c in cases]}
    folder.mkdir(parents=True,exist_ok=False)
    (folder/'packet.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    (folder/'plan.snapshot.json').write_text(snapshot_text)
    (folder/'manual.csv').write_text(encoded)
    auto = [{**c['review'],'执行方式':'自动','就绪情况':'可执行' if c.get('steps') else c.get('blocked','未实现')} for c in select_automatic(cases)]
    (folder/'api-auto.csv').write_text(csv_text(auto,FIELDS+['执行方式','就绪情况']))
    review = [manual_review(c) if mode(c)=='manual' else c['review'] for c in cases]
    report = {'run_id':packet_id,'environment':environment,'source_time':datetime.now(timezone.utc).isoformat(),
        'deployment':version,'deployment_verification':{'status':'not_provided' if version=='未提供' else 'declared'},
        'mode':'manual-preparation','execution_methods':{c['id']:mode(c) for c in cases},'results':[{'id':c['id'],'status':'NOT_RUN','actual':'待人工执行' if mode(c)=='manual' else '尚未导入本批自动执行证据'} for c in cases]}
    (folder/'cases.snapshot.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
    (folder/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    write_views(folder,review,report,extra_views=extra_views)
    (folder/'README.md').write_text('# 本批执行包\n\napi-auto.csv为API/后台自动执行侧清单（包括未具备前提的项目）；manual.csv为人工操作与回填表。\n\n只编辑执行状态、实际结果、证据、执行人、执行时间、未执行原因六列。未测保留NOT_RUN并写原因；已测填写PASS/FAIL/ERROR，清空未执行原因，填写实际结果、执行人、带时区的ISO时间及本地证据路径或HTTPS引用。实际执行环境/版本改变时另建执行包。\n\n本地证据相对manual.csv定位；不填凭据、token或未脱敏个人资料。截图先脱敏。API历史PASS不代表本批已重跑；已有UI自动化不能替代人工结果。\n\nISOP-2027的samples目录包含合成PNG，可用于图片边界检查；业务会员/待审数据仍须按授权准备，未齐时不执行。完整步骤见仓库docs/team-testing.md。\n',encoding='utf-8')
    return manifest


def signature(case):
    return {k:case.get(k) for k in ['id','steps','variables','observational','blocked']}


def merge_auto(manifest, paths):
    expected = {c['id']:c for c in manifest['cases']}
    results, seen, sources = [], set(), []
    for raw_path in paths:
        raw_path = Path(raw_path).resolve()
        raw_bytes = raw_path.read_bytes()
        report = json.loads(raw_bytes)
        source_plan = json.loads((raw_path.parent/'plan.snapshot.json').read_text())
        if source_plan['requirement']!=manifest['requirement'] or report.get('environment')!=manifest['environment'] or report.get('mode')!='execution':
            raise DeliveryError('automatic source story/environment/mode mismatch')
        if manifest['deployment']!='未提供' and report.get('deployment')!=manifest['deployment']:
            raise DeliveryError('automatic source deployment mismatch')
        if not report.get('run_id') or not report.get('source_time'): raise DeliveryError('automatic source provenance missing')
        source_cases = {c['id']:c for c in expand(source_plan)}
        incoming = set()
        excluded = []
        for item in report['results']:
            key = item['id']
            if key in incoming or key not in source_cases: raise DeliveryError('invalid automatic source case ID')
            incoming.add(key)
            if key not in expected or mode(expected[key])=='manual':
                excluded.append(key)
                continue
            if key in seen: raise DeliveryError('duplicate automatic evidence; select one explicit source per case')
            if signature(expected[key])!=signature(source_cases[key]): raise DeliveryError('automatic case version changed: '+key)
            join_results([expected[key]['review']],{'results':[item]})
            seen.add(key)
            results.append({**copy.deepcopy(item),'evidence':str(raw_path),'execution_method':'automatic',
                'source_run_id':report['run_id'],'source_time':report['source_time']})
        sources.append({'path':str(raw_path),'sha256':hashlib.sha256(raw_bytes).hexdigest(),'excluded_ids':excluded})
    return results,sources


def import_results(packet, filled, folder, auto_paths=(), *, extra_views=False):
    packet, filled, folder = Path(packet).resolve(),Path(filled).resolve(),Path(folder).resolve()
    if folder.exists(): raise DeliveryError('use a new report directory; source evidence stays immutable')
    manifest = json.loads((packet/'packet.json').read_text())
    if manifest.get('schema_version')!=1: raise DeliveryError('unknown packet version')
    snapshot_bytes = (packet/'plan.snapshot.json').read_bytes()
    if hashlib.sha256(snapshot_bytes).hexdigest()!=manifest['plan_snapshot_sha256']:
        raise DeliveryError('packet plan snapshot changed')
    source = json.loads(snapshot_bytes)
    expanded = expand(source)
    selection = manifest.get('selected_case_ids',[c['id'] for c in expanded])
    selected = [c for c in expanded if c['id'] in selection]
    if len(selection)!=len(set(selection)) or len(selected)!=len(selection) or source['requirement']!=manifest['requirement'] or selected!=manifest['cases']:
        raise DeliveryError('packet cases do not match source snapshot')
    rows = read_csv(filled,MANUAL_FIELDS)
    expected = {r['用例编号']:r for r in manifest['manual_rows']}
    if len(rows)!=len(expected) or {r['用例编号'] for r in rows}!=set(expected):
        raise DeliveryError('missing/duplicate/unknown manual case; retain NOT_RUN rows')
    results,sources = merge_auto(manifest,auto_paths)
    manual_cases = {c['id']:c for c in manifest['cases'] if mode(c)=='manual'}
    if set(expected)!=set(manual_cases): raise DeliveryError('packet manual scope mismatch')
    for row in rows:
        key = row['用例编号']
        if any(row[k]!=expected[key][k] for k in MANUAL_FIELDS if k not in EDITABLE):
            raise DeliveryError('manual case/batch/environment/version changed: '+key)
        status = row['执行状态'].strip() or 'NOT_RUN'
        if status not in STATUSES: raise DeliveryError('unknown manual status: '+key)
        actual, reason = row['实际结果'].strip(),row['未执行原因'].strip()
        evidence = row['证据'].strip()
        if status=='NOT_RUN':
            if not reason: raise DeliveryError('NOT_RUN needs a reason: '+key)
            actual = reason
        else:
            if not actual or not evidence or not row['执行人'].strip() or not row['执行时间'].strip() or reason:
                raise DeliveryError('executed manual case needs actual/evidence/person/time and empty non-execution reason: '+key)
            try:
                stamp = datetime.fromisoformat(row['执行时间'].replace('Z','+00:00'))
            except ValueError:
                raise DeliveryError('execution time must be ISO format with timezone: '+key) from None
            if stamp.tzinfo is None or stamp > datetime.now(timezone.utc): raise DeliveryError('execution time needs timezone and cannot be in future')
            url = urlsplit(evidence)
            if url.scheme:
                if url.scheme!='https' or not url.netloc or url.username or url.password: raise DeliveryError('evidence must be a local file or HTTPS reference')
            else:
                evidence_path = (filled.parent/evidence).resolve()
                if not evidence_path.is_file(): raise DeliveryError('local manual evidence missing: '+key)
                evidence = str(evidence_path)
        results.append({'id':key,'status':status,'actual':actual,'evidence':evidence,'execution_method':'manual',
            'executor':row['执行人'],'executed_at':row['执行时间'],'source_csv':str(filled)})
    review = [manual_review(c) if mode(c)=='manual' else c['review'] for c in manifest['cases']]
    report = {'schema_version':2,'run_id':manifest['packet_id']+'-review-'+uuid.uuid4().hex[:8],
        'environment':manifest['environment'],'deployment':manifest['deployment'],
        'source_time':datetime.now(timezone.utc).isoformat(),'mode':'evidence-summary','packet_id':manifest['packet_id'],
        'execution_methods':{c['id']:mode(c) for c in manifest['cases']},'sources':sources,'manual_source':{'path':str(filled),'sha256':hashlib.sha256(filled.read_bytes()).hexdigest()},'results':results}
    join_results(review,report)
    folder.mkdir(parents=True,exist_ok=False)
    (folder/'manual-import.csv').write_bytes(filled.read_bytes())
    (folder/'packet.snapshot.json').write_bytes((packet/'packet.json').read_bytes())
    (folder/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (folder/'cases.snapshot.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
    write_views(folder,review,report,extra_views=extra_views)
    return report
