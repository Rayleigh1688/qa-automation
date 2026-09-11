"""Scoped Codex-role checks with independently recorded finally restoration."""
import json
import time
from filbet.requirement_kyc import read, rows, snapshot_data, normalized

FIELDS = ['gid','name','permission','button_permission','noted','pid','state','sortlevel']


def permission_case(adapter,step,case_id):
    if 'kyc-permissions' not in adapter.args.allow_write: raise ValueError('permission write scope missing')
    actor = read(adapter,'B','/admin/me/detail')
    gid = str(actor['group_id'])
    groups = rows(read(adapter,'A','/admin/group/list',query={'page':1,'page_size':100}))
    target = [g for g in groups if str(g['gid'])==gid]
    if len(target)!=1 or target[0]['name']!='Codex': raise ValueError('designated Codex role not found')
    original = {k:target[0][k] for k in FIELDS}
    members = []
    total = None
    for page in range(1,101):
        contract = adapter.plan['contracts']['admin_users']
        users = read(adapter,'A',contract['path'],contract['method'],body={'page':page,'page_size':100})
        chunk = rows(users)
        if not isinstance(users,dict) or type(users.get('t')) is not int: raise ValueError('membership count missing')
        if total is not None and users['t']!=total: raise ValueError('membership changed during paging')
        total = users['t']
        members.extend(chunk)
        if len(members)==total: break
        if not chunk or len(members)>total: raise ValueError('membership page incomplete')
    if total!=len(members) or len({u['id'] for u in members})!=len(members): raise ValueError('cannot verify complete role membership')
    matching = [u for u in members if str(u.get('group_id',u.get('gid')))==gid]
    if len(matching)!=1 or str(matching[0]['id'])!=str(actor['id']): raise ValueError('role must contain only designated reviewer')
    before = snapshot_data(adapter,case_id)
    if before['pending']: raise ValueError('permission fixture must have no pending edit')
    kind = step['params']['kind']
    route_key = {'list':'kyc_list','audit':'kyc_audit','edit':'edit'}[kind]
    permission = {'list':'20001','audit':'20007','edit':'20006'}[kind]
    permissions = json.loads(original['permission'])
    if permission not in permissions: raise ValueError('baseline permission absent')
    revoked = {**original,'permission':json.dumps([p for p in permissions if p!=permission])}
    route = adapter.plan['contracts'][route_key]
    uid = adapter.fixtures[case_id]['uid']
    payload = step['params'].get('payload') if kind=='edit' else {'uid':uid,'page':1,'page_size':20,'source':'default'} if kind=='list' else None
    query = {'uid':uid} if kind=='audit' else None
    if kind!='edit':
        baseline = adapter.session('B').request(route['method'],route['path'],body=payload,query=query)
        if baseline['http']!=200 or baseline['body'].get('status') is not True: raise ValueError('baseline route inaccessible')
    adapter.journal(case_id,'role-baseline',role=original)
    recovery = {'id':'role-restore','status':'NOT_RUN','actual':'未修改权限'}
    adapter.recoveries.setdefault(case_id,[]).append(recovery)
    checks = {}
    update = adapter.plan['contracts']['role_update']
    def current_matches(expected):
        current = [g for g in rows(read(adapter,'A','/admin/group/list',query={'page':1,'page_size':100})) if str(g['gid'])==gid]
        return len(current)==1 and normalized({k:current[0][k] for k in FIELDS})==normalized(expected)
    changed = False
    try:
        adapter.journal(case_id,'role-revoke',phase='INTENT')
        changed = True
        response = adapter.session('A').request(update['method'],update['path'],body=revoked)
        if response['http']!=200 or response['body'].get('status') is not True or not current_matches(revoked): raise RuntimeError('role revocation not verified')
        adapter.sessions.pop('B',None)
        result = adapter.session('B').request(route['method'],route['path'],body=payload,query=query)
        checks['denied'] = result['http'] in [200,401,403] and isinstance(result['body'],dict) and result['body'].get('status') is False
        checks['no_effects'] = before==snapshot_data(adapter,case_id)
    finally:
        if changed:
            started = time.monotonic()
            try:
                adapter.journal(case_id,'role-restore',phase='INTENT')
                response = adapter.session('A').request(update['method'],update['path'],body=original)
                if response['http']!=200 or response['body'].get('status') is not True or not current_matches(original): raise RuntimeError('role restoration not verified')
                adapter.sessions.pop('B',None)
                restored = read(adapter,'B','/admin/me/detail')
                if str(restored['group_id'])!=gid: raise RuntimeError('restored actor role mismatch')
                recovery.update(status='PASS',actual='本轮原Codex配置及B身份已恢复并重新登录验证')
            except Exception:
                recovery.update(status='ERROR',actual='权限恢复未获验证；需按private-checkpoints.json原配置处理')
                adapter.recovery_failed = True
            recovery['elapsed_ms'] = round((time.monotonic()-started)*1000)
    return {'checks':checks,'summary':'撤权业务断言与finally恢复分别记录'}
