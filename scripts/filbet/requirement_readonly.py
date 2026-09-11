"""Bounded read-only probes for newly delivered requirement interfaces."""
import time
from decimal import Decimal, InvalidOperation
from filbet.requirement_session import Session

ROUTES = {
 'balance-notifications':('client','GET','/promo/notify/change/balance'),
 'jp-venue':('admin','GET','/admin/reports/venue/node'),
 'jp-game':('admin','GET','/admin/reports/game/node'),
 'jp-class':('admin','GET','/admin/reports/gameclass/node'),
 'jp-member':('admin','GET','/admin/reports/member'),
 'jp-member-game':('admin','GET','/admin/reports/member-daily-game/aggregate'),
 'pagcor-list':('pagcor','POST','/cmpl/report/pagcor/list'),
 'shop-list':('pagcor','POST','/cmpl/report/shop/list'),
 'summary':('pagcor','POST','/cmpl/report/summary/list'),
}


def validate(plan, step):
    p=step.get('params',{})
    if p.get('route') not in ROUTES or p.get('auth','valid') not in {'valid','missing','invalid'}:
        raise ValueError('unknown readonly probe')


def session_for(adapter, service):
    if service=='admin': return adapter.session('A')
    key='readonly_'+service
    if key in adapter.sessions:return adapter.sessions[key]
    if key in getattr(adapter,'readonly_login_errors',set()):
        raise RuntimeError('earlier service login failed; no repeated login attempts')
    base=adapter.config['API_URL'] if service=='client' else 'https://admin-pagcor-fat.filbet2025.com'
    session=Session(base,adapter.config,admin=service!='client',timeout=adapter.args.timeout,insecure=adapter.args.insecure)
    start=time.monotonic()
    try:
        if service=='client':session.login_client_password()
        else:session.login()
    except Exception:
        if not hasattr(adapter,'readonly_login_errors'):adapter.readonly_login_errors=set()
        adapter.readonly_login_errors.add(key)
        raise
    finally:adapter.login_ms+=round((time.monotonic()-start)*1000)
    # These sessions have separate hosts and identities from the admin fixture lane.
    session.identity='readonly-'+service
    adapter.sessions[key]=session
    return session


def probe(adapter,step,case_id):
    p=step['params'];service,method,path=ROUTES[p['route']]
    auth=p.get('auth','valid')
    if auth=='valid':session=session_for(adapter,service)
    else:
        base=adapter.config['API_URL'] if service=='client' else 'https://admin-pagcor-fat.filbet2025.com' if service=='pagcor' else adapter.config['ADMIN_URL']
        session=Session(base,adapter.config,admin=service!='client',timeout=adapter.args.timeout,insecure=adapter.args.insecure)
    response=session.request(method,path,auth=auth,query=p.get('query'),body=p.get('body'))
    body=response.get('body');data=body.get('data') if isinstance(body,dict) else None
    rows=data.get('list',data.get('d')) if isinstance(data,dict) else data if isinstance(data,list) else None
    checks={}
    if auth!='valid':
        from filbet.requirement_api import evaluate
        status,_=evaluate({'expect':'auth_rejected'}, {'status':response['http'],'decoded_body':body})
        checks['auth_denied']=status=='PASS'
    if p.get('amount_fields') and isinstance(rows,list) and rows:
        try:
            checks['amounts_valid']=all(isinstance(r[k],str) and Decimal(r[k]).is_finite() for r in rows for k in p['amount_fields'])
        except (KeyError,TypeError,InvalidOperation):checks['amounts_valid']=False
    # Public observation is an allowlist; response rows, IDs and messages stay in memory.
    response['checks']=checks
    response['summary']='HTTP '+str(response['http'])+'；业务状态='+str(body.get('status') if isinstance(body,dict) else None)+'；返回数据类型='+type(data).__name__+'；列表条数='+str(len(rows) if isinstance(rows,list) else '无列表')
    return response
