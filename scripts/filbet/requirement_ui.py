"""Bridge fixed UI steps to Playwright; API and browser retain explicit actor identity."""
import base64
from pathlib import Path
from qa_core.json_worker import JsonWorker
from qa_core.execution_plan import resolve
from qa_core.ui_contract import load_assets
from totp import current_totp


def execute_ui(adapter, step, case_id):
    from filbet.requirement_kyc import png_bytes
    fixture = adapter.fixtures.get(case_id)
    if not fixture: raise ValueError('UI pilot requires current-case fixture')
    assets = adapter.ui_assets
    if not getattr(adapter,'ui_worker',None):
        adapter.ui_worker = JsonWorker(['node','scripts/requirement-ui-worker.mjs'],cwd=Path(__file__).resolve().parents[2])
        result = adapter.ui_worker.call({'op':'init','config':{'origin':adapter.config['ADMIN_URL'],
            'assets':assets,'contracts':adapter.plan['contracts'],'scopes':adapter.args.allow_write,
            'folder':str(adapter.folder),'insecure':adapter.args.insecure,'timeout_ms':int(adapter.args.timeout*1000)}})
        if result.get('ready') is not True: raise RuntimeError('UI worker initialization failed')
    # Fixture preparation created and verified both explicit admin identities before UI login.
    session = adapter.session(step['actor'])
    conf = session.config
    code = conf.get('ADMIN_GOOGLE_CODE') or current_totp(conf.get('ADMIN_LOGIN_TOTP_SECRET') or conf['ADMIN_APPROVAL_TOTP_SECRET'],algorithm=conf.get('ADMIN_LOGIN_TOTP_ALGORITHM') or conf.get('ADMIN_APPROVAL_TOTP_ALGORITHM','SHA1'))
    auth = {'email':conf['ADMIN_EMAIL'],'password':conf['ADMIN_PASSWORD'],'code':str(code)}
    variables = step.get('bindings',{})
    page = assets['pages'][step['page']]
    compiled = {**step,'path':page['path'],'ready':page['ready']}
    if step.get('element'): compiled['target'] = resolve(assets['elements'][step['element']],variables)
    payload = {'actor':step['actor'],'step':compiled,'caseId':case_id,'auth':auth,
        'owned':{key:list(values) for key,values in fixture['owned'].items()}}
    if step['op']=='upload': payload['png'] = base64.b64encode(png_bytes(step['size'])).decode()
    try:
        result = adapter.ui_worker.call(payload,timeout=90+adapter.args.timeout*3)
    except Exception:
        adapter.ui_worker.close()
        adapter.ui_worker = None
        raise
    headers = result.pop('privateHeaders',{})
    if headers.get('t') and headers['t'] != session.token:
        session.token = headers.pop('t')
        session.headers.update(headers)
        # Reuse the browser's authenticated token; never log in API over a live UI actor.
        identity = session.request('GET','/admin/me/detail')
        if identity['http']!=200 or identity['body'].get('status') is not True or str(identity['body']['data']['id'])!=session.identity:
            raise RuntimeError('UI/API actor identity mismatch')
    return result
