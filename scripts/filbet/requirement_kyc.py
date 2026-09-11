"""Fixed KYC preparation/snapshot methods migrated from 2026-09-10 evidence.

Legacy ControlledFlow is used only inside a restored, serial preparation environment.
All test requests and snapshots use explicit actor sessions.
"""
from contextlib import contextmanager, redirect_stdout
import io
import json
import os
import re
from qa_core.redaction import sanitize_error
import struct
import zlib
from filbet.controlled import ControlledFlow
from filbet.requirement_session import Session

FIELDS = 'uid first_name middle_name last_name birthday gender phone nationality place_of_birth current_address permanent_address nearest_branch source_of_income nature_of_work occupation user_message id_type id_number shop_id status kyc_status'.split()
EDIT_FIELDS = 'uid first_name middle_name last_name birthday gender phone nationality place_of_birth current_address permanent_address nearest_branch source_of_income nature_of_work user_message attachments'.split()


def png_bytes(size=256, corrupt=False):
    if not isinstance(size,int) or not 36 <= size <= 2000000: raise ValueError('invalid synthetic PNG size')
    if corrupt: return b'not a PNG'.ljust(size,b'x')
    def chunk(kind,data): return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    prefix = b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',1,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00\x40\x90\xc0'))
    tail = chunk(b'IEND',b'')
    extra = size-len(prefix)-len(tail)-12
    if extra < 0: raise ValueError('PNG size too small')
    return prefix+chunk(b'tEXt',b'\x00'*extra)+tail


@contextmanager
def legacy_environment(config):
    previous = dict(os.environ)
    try:
        os.environ.clear(); os.environ.update(config)
        yield
    finally:
        os.environ.clear(); os.environ.update(previous)


def normalized(value):
    if isinstance(value,dict): return {k:normalized(v) for k,v in value.items() if not k.endswith('TmpUrl')}
    if isinstance(value,list): return [normalized(v) for v in value]
    if isinstance(value,str) and value.lstrip().startswith(('{','[')):
        try: return normalized(json.loads(value))
        except (ValueError,TypeError): pass
    return value


def stable(value):
    result = {k:value[k] for k in FIELDS if k in value}
    attachments = value.get('attachments')
    if isinstance(attachments,str): attachments = json.loads(attachments)
    if isinstance(attachments,dict): result['attachments'] = {k:attachments.get(k) for k in ['face','idPhoto','selfieWithIDPhotoPath']}
    return result


def read(adapter, actor, path, method='GET', body=None, query=None):
    r = adapter.session(actor).request(method,path,body=body,query=query)
    if r['http'] != 200 or not isinstance(r['body'],dict) or r['body'].get('status') is not True:
        marker = r['body'].get('data') if isinstance(r['body'],dict) else None
        adapter.journal('precondition',path,http=r['http'],business_status=r['body'].get('status') if isinstance(r['body'],dict) else None,marker=marker if isinstance(marker,str) and marker in {'token','permission','page','page_size'} else '<redacted>')
        raise RuntimeError('snapshot query failed')
    return r['body']['data']


def rows(value):
    if isinstance(value,list): return value
    if isinstance(value,dict) and isinstance(value.get('d'),list): return value['d']
    if isinstance(value,dict) and value.get('d') is None and value.get('t')==0: return []
    raise ValueError('unrecognized list contract')


def snapshot_data(adapter, case_id):
    fixture = adapter.fixtures[case_id]
    uid = fixture['uid']
    formal = read(adapter,'A','/admin/kyc/detail',query={'uid':uid})
    client = read(adapter,'client','/member/kyc/detail')
    details = rows(read(adapter,'A','/admin/kyc/details','POST',{'uid':uid}))
    matches = [r for r in details if str(r.get('uid'))==uid]
    if str(formal.get('uid')) != uid or str(client.get('uid')) != uid or len(matches)!=1: raise ValueError('detail ownership mismatch')
    pending = rows(read(adapter,'A','/admin/kyc/review/list',query={'uid':uid,'state':1,'page':1,'page_size':100}))
    processed = rows(read(adapter,'A','/admin/kyc/review/list',query={'uid':uid,'state':2,'page':1,'page_size':100}))
    audit = rows(read(adapter,'A','/admin/kyc/ekyc/log',query={'uid':uid}))
    if any(str(r.get('uid'))!=uid for r in pending+processed) or any('uid' in r and str(r['uid'])!=uid for r in audit): raise ValueError('list ownership mismatch')
    fixture['latest'] = formal
    fixture['owned']['id'].update(str(r['id']) for r in pending+processed)
    adapter.journal(case_id,'snapshot',uid=uid,pending=[str(r['id']) for r in pending],processed=[str(r['id']) for r in processed],audit_count=len(audit),extra_batch_rows=len(details)-len(matches))
    return {'formal':{'admin':stable(formal),'client':stable(client),'details':stable(matches[0])},'pending':normalized(pending),'processed':normalized(processed),'audit':normalized(audit),'batch_exact':len(details)==1}


def fixture(adapter, step, case_id):
    if case_id in adapter.fixtures: raise ValueError('fixture already created')
    target_status = step.get('params',{}).get('target_status',2)
    if type(target_status) is not int or target_status not in {2,3,5}: raise ValueError('unknown fixture state contract')
    a,b = adapter.session('A'),adapter.session('B')
    flow = ControlledFlow()
    args = flow.build_parser().parse_args(['--env',adapter.args.env,'--timeout',str(adapter.args.timeout)])
    args.insecure = adapter.args.insecure
    args.kyc_first_name,args.kyc_middle_name,args.kyc_last_name = 'Codex','-','ReviewTest'
    image = adapter.folder/(case_id+'-fixture.png')
    image.write_bytes(png_bytes())
    args.kyc_image = str(image)
    config = {**adapter.config,'ADMIN_TOKEN':a.token,'ADMIN_DEVICE_ID':a.headers['x-device-id']}
    config.pop('API_TOKEN',None)
    with legacy_environment(config), redirect_stdout(io.StringIO()):
        try:
            reserve_phone(flow,args)
            adapter.journal(case_id,'fixture-register',phase='INTENT',phone=args.register_phone)
            rs = flow.register_new_user(args)
            if not rs or not all(r.get('business_status') is True for r in rs): raise RuntimeError('registration failed')
            token = os.environ.get('API_TOKEN','')
            if not token: raise RuntimeError('registration token missing')
            client = Session(adapter.config['API_URL'],adapter.config,admin=False,timeout=adapter.args.timeout,insecure=adapter.args.insecure)
            client.token = token
            adapter.sessions['client'] = client
            detail = read(adapter,'client','/member/kyc/detail')
            uid = str(detail['uid'])
            if str(detail.get('phone')) != args.register_phone or detail.get('kyc_status') != 0 or any(f['uid']==uid for f in adapter.fixtures.values()):
                raise RuntimeError('registration did not produce a fresh owned member')
            adapter.fixtures[case_id] = {'uid':uid,'owned':{'uid':{uid},'id':set()}}
            adapter.journal(case_id,'fixture-kyc',phase='INTENT',uid=uid)
            rs = flow.submit_kyc(args)
            if not rs or not all(r.get('business_status') is True for r in rs): raise RuntimeError('KYC preparation failed')
            target_status = step.get('params',{}).get('target_status',2)
            if target_status in {3,5}:
                flow.LAST_APPROVAL_CODE = getattr(adapter,'last_approval_code','')
                adapter.journal(case_id,'fixture-initial-review',phase='INTENT',target_status=target_status)
                if target_status==5:
                    records = flow.approve_kyc(args,uid)
                    if not records or not all(r.get('business_status') is True for r in records): raise RuntimeError('initial KYC approval preparation failed')
                else:
                    body = flow.add_approval_code({'uid':uid,'issue':{'message':'QA isolated resubmission required','fields':{'attachments.idPhoto':'QA replacement required'}},'comment':'QA isolated state preparation','final':False},args)
                    contract = adapter.plan['contracts']['initial_kyc_reject']
                    response = a.request(contract['method'],contract['path'],body=body)
                    if response['http']!=200 or response['body'].get('status') is not True: raise RuntimeError('initial KYC rejection preparation failed')
                adapter.last_approval_code = flow.LAST_APPROVAL_CODE
                current = read(adapter,'client','/member/kyc/detail')
                if current.get('kyc_status')!=target_status: raise RuntimeError('prepared KYC status mismatch')
        except SystemExit as error:
            adapter.journal(case_id,'preparation-error',category='controlled-helper',reason=re.sub(r'\d{7,}', '<id>', sanitize_error(error,dict(os.environ))))
            raise RuntimeError('controlled preparation failed') from error
    baseline = snapshot_data(adapter,case_id)
    if baseline['pending'] or baseline['processed']: raise RuntimeError('fresh fixture has review history')
    return {'summary':'本轮独立会员注册及KYC前置完成（不计业务用例）','fixture':{'uid':uid},'baseline':baseline,'actors':{key:{'id':session.identity,'name':session.identity_name} for key,session in [('A',a),('B',b)]}}


def snapshot(adapter,step,case_id):
    return {'snapshot':snapshot_data(adapter,case_id),'summary':'本轮会员三端正式资料、申请及审计快照完成'}


def edit_payload(adapter,step,case_id):
    source = adapter.fixtures[case_id]['latest']
    if not all(k in source for k in EDIT_FIELDS): raise ValueError('edit field missing')
    body = {k:source[k] for k in EDIT_FIELDS}
    body.update(step.get('params',{}))
    return {'payload':body,'summary':'从本轮详情构造编辑参数'}


METHOD_REGISTRY = {
    'kyc_fixture':{'call':fixture,'scope':'kyc-review'},
    'kyc_snapshot':{'call':snapshot,'scope':None,'read_only':True},
    'kyc_edit_payload':{'call':edit_payload,'scope':None},
}


def verify(adapter,step,case_id):
    p = step['params']
    before,after = p['before'],p['after']
    changes = p.get('changes',{})
    expected = {surface:{**values,**changes} for surface,values in before['formal'].items()}
    checks = {'formal':after['formal']==expected,
              'audit_append':len(after['audit'])==len(before['audit'])+1 and all(row in after['audit'] for row in before['audit'])}
    return {'checks':checks,'summary':'核对三端正式字段及其他字段保持、旧审计不可变'}


METHOD_REGISTRY['kyc_verify'] = {'call':verify,'scope':None}


def query_fixture(adapter,step,case_id):
    state = snapshot_data(adapter,case_id)
    records = state['processed']
    if not records: raise ValueError('query fixture has no processed records')
    times = [r['created_at'] for r in records]
    formal = state['formal']['admin']
    return {'query_data':{'phone':formal['phone'],'middle_name':formal['middle_name'],'last_name':formal['last_name'],
        'created_name':records[0]['created_name'],'start':min(times)-1,'end':max(times)+1,
        'future':max(times)+1000,'past':min(times)-1000,'ids':[r['id'] for r in records]},'summary':'从本轮已处理申请建立独立筛选基准'}


METHOD_REGISTRY['kyc_query_fixture'] = {'call':query_fixture,'scope':None}


def member_payload(adapter,step,case_id):
    source = snapshot_data(adapter,case_id)['formal']['client']
    keys = 'attachments birthday current_address first_name middle_name last_name nationality gender id_number id_type nature_of_work nearest_branch occupation permanent_address phone place_of_birth source_of_income'.split()
    body = {k:source[k] for k in keys}
    shops = rows(read(adapter,'client','/member/kyc/shops','POST'))
    matches = [s for s in shops if (s.get('label') or s.get('name') or s.get('address'))==body['nearest_branch']]
    if len(matches)!=1: raise ValueError('KYC branch is not unique')
    branch = matches[0]
    body.update(country_code='63',shop_id=int(branch.get('value') or branch.get('id') or branch.get('shop_id') or 0))
    if not body['shop_id']: raise ValueError('KYC branch ID missing')
    return {'payload':body,'summary':'复用本轮成功KYC字段与唯一分行，准备会员重提反例'}


METHOD_REGISTRY['kyc_member_payload'] = {'call':member_payload,'scope':None}


def reserve_phone(flow,args):
    """Durable reservation prevents reuse while the member search index catches up."""
    reservation = flow.PHONE_CURSOR_DIR / 'requirement-reservations-fat.json'
    reserved = json.loads(reservation.read_text()) if reservation.exists() else {}
    cursor = flow.load_phone_cursor(flow.phone_cursor_path(args.env))
    start = max(int(cursor or '9000000000'), int(reserved.get('last_phone','9000000000'))) + 1
    args.register_phone = str(start)
    args.register_phone,_ = flow.allocate_registration_phone(args)
    reservation.parent.mkdir(parents=True,exist_ok=True)
    fd = os.open(reservation,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as stream: json.dump({'last_phone':args.register_phone},stream)


def validate_fixture(plan,step):
    status = step.get('params',{}).get('target_status',2)
    if type(status) is not int or status not in {2,3,5}:
        raise ValueError('unknown fixture state contract')


METHOD_REGISTRY['kyc_fixture']['validate'] = validate_fixture
