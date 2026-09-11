#!/usr/bin/env python3
"""Validate, select and execute versioned requirement plans; old CLI stays compatible."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import uuid
import time
from qa_core.execution_plan import load, legacy_query_suite
from qa_core.case_catalogue import export_catalogues
from qa_core.plan_runner import execute
from qa_core.case_report import write_views
from qa_core.local_lock import local_run_lock

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('story')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--env', default='.env.fat')
    parser.add_argument('--insecure', action='store_true')
    parser.add_argument('--timeout', type=float, default=15)
    parser.add_argument('--version', default='未提供', help='Declared deployment version; does not claim remote verification')
    parser.add_argument('--expected-plan-sha256', help='Reject a plan changed since task confirmation')
    parser.add_argument('--result-index', type=Path, help='Write this invocation result path to a new local index file')
    parser.add_argument('--only', nargs='+')
    parser.add_argument('--layer', choices=['API','UI','FLOW'])
    parser.add_argument('--export-cases', action='store_true')
    parser.add_argument('--extra-views', action='store_true', help='Also export cases/failures/pending CSV and summary JSON')
    parser.add_argument('--include-ui-automation', action='store_true', help='Opt into retained UI automation; default api-first policy excludes manual assignments')
    parser.add_argument('--allow-write', action='append', default=[])
    parser.add_argument('--rebuild', type=Path, help='Rebuild views from an existing raw result into a new sibling directory')
    args = parser.parse_args()
    if not args.version.strip() or len(args.version)>200 or any(ord(ch)<32 for ch in args.version):
        raise ValueError('invalid declared deployment version')
    args.version = args.version.strip()
    if args.result_index and (not args.execute or args.rebuild or args.result_index.exists() or not args.result_index.parent.is_dir()):
        raise ValueError('result index requires execution and a new file')
    if not re.fullmatch(r'ISOP-\d+', args.story) or not 0 < args.timeout <= 60:
        raise ValueError('invalid story or timeout')
    if args.rebuild:
        report = json.loads((args.rebuild/'result.json').read_text())
        snapshot = json.loads((args.rebuild/'cases.snapshot.json').read_text())
        write_views(args.rebuild.parent/(args.rebuild.name+'-views-'+uuid.uuid4().hex[:8]), snapshot, report, extra_views=args.extra_views)
        return 0
    from filbet.requirement_adapter import Adapter, METHODS
    path = ROOT/'requirements'/args.story/'plan.json'
    plan, cases, digest = load(path, METHODS)
    if args.expected_plan_sha256 and digest != args.expected_plan_sha256:
        raise ValueError('execution plan changed since confirmation')
    if args.export_cases:
        export_catalogues(path.parent,plan=plan,cases=cases)
        if plan.get('legacy_metadata'):
            (path.parent/'api/cases.json').write_text(json.dumps(legacy_query_suite(plan),ensure_ascii=False,indent=2)+'\n')
    if args.only:
        if not set(args.only) <= {c['id'] for c in cases}: raise ValueError('unknown case selection')
        cases = [c for c in cases if c['id'] in args.only]
    if args.layer: cases = [c for c in cases if c['review']['类型'] == args.layer]
    if plan.get('execution_policy')=='api-first' and not args.only and not args.layer and not args.include_ui_automation:
        from qa_core.team_delivery import select_automatic
        cases = select_automatic(cases)
    if not cases: raise ValueError('empty selection')
    if not args.execute:
        print(f"{args.story}: validated {len(cases)} cases; executable {sum(bool(c.get('steps')) for c in cases)}; no login")
        return 0
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
    folder = ROOT/'reports/qa'/args.story/run_id
    with local_run_lock():
        adapter = Adapter(plan,args,folder)
        adapter.preflight(cases)
        folder.mkdir(parents=True,exist_ok=False)
        report = {'schema_version':2,'requirement':args.story,'run_id':run_id,'environment':adapter.environment,'source_time':datetime.now(timezone.utc).isoformat(),'mode':'execution','cases_sha256':digest,'deployment':args.version,
                  'deployment_verification':{'status':'not_provided' if args.version=='未提供' else 'declared','source':'cli'}}
        if getattr(adapter,'ui_assets',None):
            import hashlib
            asset_text = json.dumps(adapter.ui_assets,ensure_ascii=False,indent=2)+'\n'
            (folder/'ui-assets.snapshot.json').write_text(asset_text)
            report['ui_assets_sha256'] = hashlib.sha256(asset_text.encode()).hexdigest()
        snapshot = [c['review'] for c in cases]
        (folder/'plan.snapshot.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
        (folder/'cases.snapshot.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n')
        def checkpoint(results):
            report['results'] = results
            for item in results: item['evidence'] = str(folder/'result.json')
            temp = folder/'result.tmp'
            temp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
            temp.replace(folder/'result.json')
        try:
            report['results'] = execute(cases,adapter,run_id,checkpoint)
        finally:
            if getattr(adapter,'ui_worker',None): adapter.ui_worker.close()
        for item in report['results']: item['evidence'] = str(folder/'result.json')
        source_steps = {(c['id'],s['id']):s for c in cases for s in c.get('steps',[])}
        report['timings_ms'] = {'login':adapter.login_ms,'preparation_including_login':0,'api_requests':0,'ui':0,'readback':0}
        for item in report['results']:
            for step in item.get('steps',[]):
                source = source_steps[(item['id'],step['id'])]
                key = 'preparation_including_login' if source.get('method')=='kyc_fixture' else 'api_requests' if source['action']=='api' else 'ui' if source['action']=='ui' else 'readback'
                report['timings_ms'][key] += step.get('elapsed_ms',0)
        snapshot = [c['review'] for c in cases]
        (folder/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        (folder/'cases.snapshot.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n')
        report_started = time.monotonic()
        write_views(folder,snapshot,report,extra_views=args.extra_views)
        report['timings_ms']['report'] = round((time.monotonic()-report_started)*1000)
        (folder/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        if any(item.get('steps') for item in report['results']):
            latest = folder.parent/'latest.json'
            temp = folder.parent/('latest-'+uuid.uuid4().hex+'.tmp')
            temp.write_text(json.dumps({'run_id':run_id,'results':run_id+'/results.html','raw':run_id+'/result.json'})+'\n')
            temp.replace(latest)
            (folder.parent/'latest.html').write_text('<!doctype html><meta charset="utf-8"><title>最近一次实测</title><a href="'+run_id+'/results.html">打开最近一次实测结果</a>')
        print('Results:',folder/'results.html')
        if args.result_index:
            with args.result_index.open('x',encoding='utf-8') as index:
                json.dump({'raw':str((folder/'result.json').resolve()),'run_id':run_id},index)
        print({s:sum(r['status']==s for r in report['results']) for s in ['PASS','FAIL','NOT_RUN','ERROR']})
        if any(r['status'] in {'FAIL','ERROR'} for r in report['results']): return 1
        return 2 if any(r['status']=='NOT_RUN' for r in report['results']) else 0


if __name__ == '__main__':
    try: raise SystemExit(main())
    except (ValueError,OSError,KeyError) as error:
        print('Preflight failed:',type(error).__name__,str(error) if isinstance(error,ValueError) else 'check local configuration')
        raise SystemExit(1)
