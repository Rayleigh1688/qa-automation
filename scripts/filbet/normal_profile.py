"""Share one owned processed fixture across read-only UI checks in the normal profile."""
import copy
from filbet.requirement_kyc import snapshot_data

UI_READ_CASES = {f'2027-UI-{i:03}' for i in range(7,14)}


def reuse_ui(adapter, step, case_id):
    if case_id not in UI_READ_CASES or not getattr(adapter, 'normal_ui_pool', None):
        raise RuntimeError('shared processed fixture unavailable')
    source, expected = adapter.normal_ui_pool
    adapter.fixtures[case_id] = adapter.fixtures[source]
    if snapshot_data(adapter, case_id) != expected:
        adapter.normal_ui_pool = None
        raise RuntimeError('shared processed fixture changed; stop reuse')
    return {'fixture': {'uid': adapter.fixtures[source]['uid']}, 'processed': expected, 'summary': '复用本轮已处理申请；前置快照未变化，无新增注册'}


def prepare_cases(cases):
    cases = copy.deepcopy(cases)
    for case in cases:
        if case['id'] in UI_READ_CASES:
            start = next(i for i,s in enumerate(case['steps']) if s['id']=='open-review')
            import json
            checks = json.loads(json.dumps(case['steps'][start:]).replace('${pending.pending.0.id}', '${processed.processed.0.id}'))
            case['steps'] = [{'id':'reuse-processed','action':'method','method':'kyc_reuse_processed_ui','actor':'A','extract':{'fixture':'fixture','processed':'processed'}}] + checks
    return cases


def after_case(adapter, case, item):
    ident = case['id']
    if ident == '2027-UI-006':
        if item['status']=='PASS':
            adapter.normal_ui_pool = (ident, snapshot_data(adapter, ident))
        else:
            adapter.normal_ui_pool = None
    elif ident in UI_READ_CASES and getattr(adapter,'normal_ui_pool',None):
        expected = adapter.normal_ui_pool[1]
        if snapshot_data(adapter, ident) != expected:
            adapter.normal_ui_pool = None
            item.update(status='FAIL', actual='只读UI操作后资料/申请/审计发生变化，已停止共享前置')


def apply_role_preconditions(adapter, cases):
    """A permission denial cannot stand in for self-review or identity-spoof protection."""
    import json
    b = adapter.session('B')
    me = b.request('GET','/admin/me/detail')
    groups = b.request('GET','/admin/group/list',query={'page':1,'page_size':100})
    if me['body'].get('status') is not True or groups['body'].get('status') is not True:
        raise RuntimeError('role assignment read failed')
    data = groups['body']['data']
    rows = data.get('d',[]) if isinstance(data,dict) else data
    group = next(x for x in rows if str(x.get('gid'))==str(me['body']['data']['group_id']))
    grants = group.get('permission',[])
    if isinstance(grants,str):grants=json.loads(grants)
    missing = [x for x in ['20010','20011'] if x not in {str(v) for v in grants}]
    if missing:
        for case in cases:
            if any(s.get('actor')=='B' and s.get('contract')=='review' and s.get('auth','valid')=='valid' for s in case.get('steps',[])):
                case['blocked']='权限前置未满足：Codex角色未分配'+','.join(missing)+'；不能把permission拒绝当作自审/身份保护通过。'
    for case in cases:
        if case['id']=='2027-UI-015':case['blocked']='完整UI撤权控件矩阵尚未实现；当前角色权限核查单独记录，不替代UI矩阵。'
    return {'reviewer_role':group.get('name'),'missing_permissions':missing,'blocked_cases':[c['id'] for c in cases if c.get('blocked','').startswith('权限前置')]}
