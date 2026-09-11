"""Bounded two-request KYC races on a single freshly owned fixture."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from filbet.requirement_kyc import snapshot_data


def race(adapter,step,case_id):
    if 'kyc-review' not in adapter.args.allow_write: raise ValueError('KYC write scope missing')
    params = step['params']
    requests = params['requests']
    if len(requests)!=2: raise ValueError('exactly two requests required')
    fixture = adapter.fixtures[case_id]
    ready = []
    for index,item in enumerate(requests):
        route = adapter.plan['contracts'][item['contract']]
        if item['contract'] not in {'edit','review'} or route.get('scope')!='kyc-review': raise ValueError('race contract not allowed')
        owner = route['ownership']
        if str(item['body'].get(owner)) not in fixture['owned'][owner]: raise ValueError('race target not owned')
        ready.append((adapter.session(item['actor']),route,item['body']))
        adapter.journal(case_id,step['id']+'-'+str(index),phase='INTENT',contract=item['contract'])
    barrier = Barrier(2)
    def send(item):
        session,route,body = item
        barrier.wait(timeout=5)
        return session.request(route['method'],route['path'],body=body,encoding=route['encoding'])
    outcomes = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(send,item) for item in ready]
        for index,future in enumerate(futures):
            try:
                response = future.result()
                body = response.get('body')
                outcomes.append({'http':response['http'],'business_status':body.get('status') if isinstance(body,dict) else None})
            except Exception:
                outcomes.append({'http':None,'business_status':None})
            adapter.journal(case_id,step['id']+'-'+str(index),phase='RETURNED',**outcomes[-1])
    after = snapshot_data(adapter,case_id)
    before = params['before']
    winners = [i for i,r in enumerate(outcomes) if r['http']==200 and r['business_status'] is True]
    checks = {'one_winner':len(winners)==1,'audit_append':len(after['audit'])==len(before['audit'])+1 and all(row in after['audit'] for row in before['audit'])}
    if requests[0]['contract']=='edit':
        checks.update(one_transition=len(after['pending'])==1 and not after['processed'],formal=after['formal']==before['formal'])
    else:
        expected = before['formal']
        if len(winners)==1:
            decision = requests[winners[0]]['body']['review_status']
            if decision==2: expected = {surface:{**values,**params['changes']} for surface,values in expected.items()}
            checks['one_transition'] = not after['pending'] and len(after['processed'])==1 and after['processed'][0]['state']==decision
        else: checks['one_transition']=False
        checks['formal'] = after['formal']==expected
    return {'checks':checks,'outcomes':outcomes,'execution_error':any(r['http'] is None for r in outcomes),'summary':'两请求响应='+str(outcomes)+'；仅只读核对现场，不继续处理申请'}


def validate_race(plan,step):
    requests = step.get('params',{}).get('requests',[])
    if len(requests)!=2 or len({r.get('contract') for r in requests})!=1:
        raise ValueError('race requires two requests to the same reviewed contract')
    for request in requests:
        if request.get('contract') not in {'edit','review'} or request.get('actor') not in plan['actors'] or 'body' not in request:
            raise ValueError('invalid race request reference')
