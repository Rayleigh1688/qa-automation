"""One entry point for document sync, AI cases, preflight, scans and local status."""
from requirement_paths import requirement_dirs
import argparse
import json
import os
from pathlib import Path
from qa_core.environment import read_values
from qa_core.local_lock import local_run_lock, LocalRunBusy
from qa_delivery.state import Store, validate_config
from qa_delivery.batch import run_batch, refresh_preview
from qa_delivery.connectors import Telegram, Jira, RemoteError
from .state import State
from .documents import sync
from .generation import generate
from .service import preflight, process_candidates
from .web import export, serve
from .evidence import check_all

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['sync','generate','check','scan','run','status','evidence'])
    parser.add_argument('story',nargs='?')
    parser.add_argument('--config',default='config/telegram/local.json')
    parser.add_argument('--state',default='reports/workflow')
    parser.add_argument('--source',default='/Users/rayleigh/API/FB/filbet')
    parser.add_argument('--ref',default='HEAD')
    parser.add_argument('--fetch',action='store_true',help='Fetch origin before syncing the pinned document revision')
    parser.add_argument('--offline',action='store_true',help='Use saved scan; no scan/AI/business calls')
    parser.add_argument('--execute',action='store_true',help='Run ready authorized API events; no Jira writes/messages')
    parser.add_argument('--serve',action='store_true')
    parser.add_argument('--validate-output',action='store_true',help='Revalidate the saved AI output against identical source context, without calling AI')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--allow-pending',action='store_true',help='Evidence check: allow explicitly unreviewed sources; never ignore drift/errors')
    parser.add_argument('--include-history', action='store_true', help='Evidence checks: include archived requirements')
    args = parser.parse_args()
    if args.include_history and args.mode != 'evidence': parser.error('--include-history requires evidence')
    if args.validate_output and args.mode!='generate': parser.error('--validate-output requires generate')
    if args.execute and args.mode not in ('scan','run'): parser.error('--execute only applies to scan/run')
    if args.offline and args.execute: parser.error('--offline cannot execute')
    if args.serve and args.mode != 'status': parser.error('--serve requires status')
    if args.allow_pending and args.mode != 'evidence': parser.error('--allow-pending requires evidence')
    if args.mode == 'evidence':
        results = check_all(ROOT, args.story, include_history=args.include_history)
        for value in results:
            print(value['story'], value['status'], '；'.join(value['errors'] + value['pending']))
        if any(r['errors'] for r in results): return 1
        return 2 if not args.allow_pending and any(r['pending'] for r in results) else 0
    state = State(ROOT,ROOT/args.state)
    try:
        if args.mode=='status':
            print(export(state))
            if args.serve: serve(state,args.port)
            return 0
        config = validate_config(json.loads((ROOT/args.config).read_text(encoding='utf-8')))
        with local_run_lock(namespace='qa-workflow',inherit=False):
            if args.mode in ('sync','run'):
                result = sync(state,args.source,args.ref,args.fetch and not args.offline)
                print('接口文档：',result['commit'],'无变化' if result.get('unchanged') else f"{len(result['changes'])} 份文档（{'基线' if result['baseline'] else '增量'}）")
            if args.mode=='generate':
                if not args.story: parser.error('generate requires a Story')
                if args.offline and not args.validate_output: parser.error('generate calls AI; use --validate-output for saved output')
                value = generate(state,args.story,config,validate_output=args.validate_output)
                print(args.story,'AI草稿用例：',len(value['cases']))
            if args.mode=='check':
                stories = [args.story] if args.story else [p.name for p in requirement_dirs(ROOT)]
                results = [preflight(state,config,story) for story in stories]
                for value in results:
                    state.append(value['story'],'preflight',{**value,'source':'config/workflow.json'})
                    print(value['story'],value['status'],'；'.join(value['reasons']))
                export(state)
                return 2 if any(r['status']=='BLOCKED' for r in results) else 0
            if args.mode in ('scan','run'):
                credentials = ROOT/'.env.telegram'
                if not args.offline and credentials.is_file(): os.environ.update(read_values(credentials))
                scan_state = ROOT/'reports/telegram'
                with local_run_lock(namespace='qa-telegram-batch',inherit=False):
                    if args.offline:
                        preview = refresh_preview(config,scan_state)
                    else:
                        store = Store(scan_state/'queue.sqlite3')
                        try: preview = run_batch(store,Telegram(os.environ.get('TELEGRAM_BOT_TOKEN','')),config,scan_state)
                        finally: store.close()
                    if args.story: preview = {**preview,'candidates':[c for c in preview['candidates'] if c['story']==args.story]}
                    if args.mode=='run' and not args.offline:
                        for story in sorted({c['story'] for c in preview['candidates'] if c['story']!='ISOP-2022'}):
                            generate(state,story,config)
                    outcomes = process_candidates(state,config,preview,execute=args.execute,
                        jira=Jira(config['jira']) if args.execute else None)
                    for result in outcomes: print(result['story'],result['status'],'；'.join(result['reasons']))
            print('状态快照：',export(state))
        return 0
    finally: state.close()


def entrypoint():
    try: return main()
    except KeyboardInterrupt: return 130
    except (OSError,ValueError,KeyError,RemoteError,LocalRunBusy) as error:
        print('流程停止：',type(error).__name__,str(error) if isinstance(error,(ValueError,LocalRunBusy)) else '检查本地配置或日志')
        return 1
