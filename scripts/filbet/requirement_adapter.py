"""FILBET plan adapter. Only registered contracts and current-case fixtures can write."""
import json
import time
from pathlib import Path
from qa_core.environment import load_environment, read_values
from filbet.requirement_session import Session

METHODS = {}  # Populated by explicitly imported, fixed business methods below.


class Adapter:
    def __init__(self, plan, args, folder):
        self.plan, self.args, self.folder = plan, args, Path(folder)
        self.config = load_environment(args.env)
        self.environment = 'FAT'
        self.sessions, self.fixtures = {}, {}
        self.intents = []
        self.recoveries = {}
        self.recovery_failed = False
        self.login_ms = 0
        self.fixture_preparation_failed = False
        self.login_failed_actors = set()

    def case_blocker(self, case):
        methods = {s.get('method') for s in case.get('steps', [])}
        if self.recovery_failed:
            return '本轮权限恢复尚未验证，暂停后续检查；需先核对原配置与账号身份'
        if self.login_failed_actors and ('kyc_fixture' in methods or any(s.get('actor') in self.login_failed_actors for s in case.get('steps', []))):
            return '本轮管理员登录前置已失败，暂停依赖检查；不重复尝试登录'
        if self.fixture_preparation_failed and methods & {'kyc_fixture','kyc_reuse_processed_ui'}:
            return '本轮会员注册前置已失败，暂停依赖造数的检查；需定位原始失败后明确续测范围'
        if 'kyc_reuse_processed_ui' in methods and not getattr(self, 'normal_ui_pool', None):
            return '本轮共享的已处理申请未准备成功，尚未执行只读UI检查'
        return ''

    def preflight(self, cases):
        if any(s['action']=='ui' for c in cases for s in c.get('steps',[])):
            from qa_core.ui_contract import load_assets
            self.ui_assets = load_assets(self.plan)
        endpoints = (self.config.get('ADMIN_URL'), self.config.get('API_URL'))
        if endpoints == ('https://admin-fat.filbet2025.com', 'https://client-fat.filbet2025.com'):
            if Path(self.args.env).name == '.env.uat':
                raise ValueError('UAT selection cannot use FAT endpoints')
            self.environment = 'FAT'
        elif (endpoints == ('https://admin-antd.filbet.zone', 'https://client-beta.filbet.zone')
              and Path(self.args.env).name == '.env.uat' and self.plan.get('requirement') == 'ISOP-2027'):
            self.environment = 'UAT'
            if self.config.get('ADMIN_GOOGLE_CODE') or not (self.config.get('ADMIN_LOGIN_TOTP_SECRET') or self.config.get('ADMIN_APPROVAL_TOTP_SECRET')):
                raise ValueError('UAT requires dynamic admin login credentials')
            if any(s.get('method') == 'kyc_fixture' for c in cases for s in c.get('steps', [])):
                if (self.config.get('REGISTER_OTP') or self.config.get('CLIENT_OTP')
                    or self.config.get('REGISTER_OTP_SOURCE') != 'admin_sms'
                    or not self.config.get('ADMIN_APPROVAL_TOTP_SECRET')):
                    raise ValueError('UAT fixtures require dynamic registration OTP via admin_sms')
        else:
            raise ValueError('unsupported or mixed requirement environment endpoints')
        for case in cases:
            for step in case.get('steps',[]):
                scope = self.plan['contracts'][step['contract']].get('scope') if step['action']=='api' else 'kyc-review' if step['action']=='ui' else METHODS[step['method']]['scope']
                if scope and scope not in self.args.allow_write:
                    raise ValueError('selected case requires --allow-write ' + scope)
        if any(s['actor']=='B' or s.get('method')=='kyc_fixture' for c in cases for s in c.get('steps',[])):
            reviewer = self.config.get('QA_REVIEWER_ENV',f'.env.{self.environment.lower()}.reviewer.local')
            overlay = read_values(reviewer)
            if self.environment == 'UAT' and (
                not all(overlay.get(k) for k in ('ADMIN_URL', 'ADMIN_EMAIL', 'ADMIN_PASSWORD', 'ADMIN_LOGIN_TOTP_SECRET'))
                or overlay.get('ADMIN_GOOGLE_CODE')):
                raise ValueError('UAT reviewer requires its own dynamic login credentials')
            self.reviewer = {**self.config, **overlay}
            if self.reviewer.get('ADMIN_URL') != self.config['ADMIN_URL'] or self.reviewer['ADMIN_EMAIL'].lower() == self.config['ADMIN_EMAIL'].lower():
                raise ValueError('reviewer must be a distinct account on same service')

    def session(self, actor):
        if actor in self.login_failed_actors:
            raise RuntimeError('earlier actor login failed; no repeated login attempts')
        if actor not in self.sessions:
            if actor == 'client': raise ValueError('client fixture not prepared')
            conf = self.reviewer if actor == 'B' else self.config
            session = Session(conf['ADMIN_URL'],conf,timeout=self.args.timeout,insecure=self.args.insecure)
            started = time.monotonic()
            try:
                session.login()
            except Exception:
                self.login_failed_actors.add(actor)
                raise
            self.login_ms += round((time.monotonic()-started)*1000)
            identity = session.request('GET','/admin/me/detail')
            if identity['http'] != 200 or identity['body'].get('status') is not True: raise RuntimeError('identity query failed')
            session.identity = str(identity['body']['data']['id'])
            session.identity_name = identity['body']['data'].get('name') or identity['body']['data'].get('username','')
            if any(s.admin and s.identity == session.identity for s in self.sessions.values()): raise RuntimeError('actors resolved to same identity')
            self.sessions[actor] = session
        return self.sessions[actor]

    def journal(self, case_id, step_id, **data):
        import os
        entry = {'case':case_id,'step':step_id,**data}
        self.intents.append(entry)
        fd = os.open(self.folder/'private-checkpoints.json',os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'w') as stream: json.dump(self.intents,stream,ensure_ascii=False,indent=2)

    def execute(self, step, case_id):
        if self.recovery_failed: raise RuntimeError('prior role restoration unresolved')
        if step['action']=='ui':
            from filbet.requirement_ui import execute_ui
            return execute_ui(self,step,case_id)
        if step['action']=='method': return METHODS[step['method']]['call'](self,step,case_id)
        route = self.plan['contracts'][step['contract']]
        if route['write']:
            fixture = self.fixtures.get(case_id)
            if not fixture: raise ValueError('write requires current-case fixture')
            body = step.get('body',{})
            key = route.get('ownership')
            if key and str(body.get(key)) not in fixture['owned'].get(key,set()): raise ValueError('write ownership mismatch')
            if route['scope'] not in self.args.allow_write: raise ValueError('write scope missing')
            self.journal(case_id,step['id'],phase='INTENT',contract=step['contract'])
        session = self.session(step['actor'])
        if route['service'] != ('admin' if session.admin else 'client'): raise ValueError('session service mismatch')
        upload = None
        if route['encoding']=='multipart':
            from filbet.requirement_kyc import png_bytes
            spec = step['upload']
            upload = (png_bytes(spec['size'],spec.get('corrupt',False)), 'qa.png','image/png')
        response = session.request(route['method'],route['path'],body=step.get('body'),query=step.get('query'),headers=step.get('headers'),encoding=route['encoding'],auth=step.get('auth','valid'),upload=upload)
        if route['write']:
            body = response.get('body')
            marker = body.get('data') if isinstance(body,dict) else None
            self.journal(case_id,step['id'],phase='RETURNED',http=response['http'],business=body.get('status') if isinstance(body,dict) else None,marker=marker if isinstance(marker,str) and marker in {'token','permission','id','reason','review_status','uid'} else '<redacted>',body_type=type(body).__name__)
            if route['encoding']=='multipart' and isinstance(body,dict) and isinstance(body.get('data'),dict):
                self.journal(case_id,step['id']+'-object',object_key=body['data'].get('object_key'))
        return response


from filbet.requirement_kyc import METHOD_REGISTRY
METHODS.update(METHOD_REGISTRY)

from filbet.requirement_permissions import permission_case
METHODS['kyc_permission'] = {'call':permission_case,'scope':'kyc-permissions','business':True}

from filbet.requirement_race import race, validate_race
METHODS['kyc_race'] = {'call':race,'scope':'kyc-review','business':True,'validate':validate_race}

from filbet.requirement_records import record_check
METHODS['bet_record_check'] = {'call':record_check,'scope':None,'business':False,'read_only':True}

from filbet.requirement_readonly import probe as readonly_probe, validate as validate_readonly_probe
METHODS['readonly_query'] = {'call':readonly_probe,'scope':None,'business':True,'read_only':True,'validate':validate_readonly_probe}

from filbet.protected_edit import verify as verify_protected_edit
METHODS['kyc_verify_protected_edit'] = {'call':verify_protected_edit,'scope':None,'read_only':True}
