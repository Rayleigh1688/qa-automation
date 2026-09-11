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

    def preflight(self, cases):
        if any(s['action']=='ui' for c in cases for s in c.get('steps',[])):
            from qa_core.ui_contract import load_assets
            self.ui_assets = load_assets(self.plan)
        if self.config.get('ADMIN_URL') != 'https://admin-fat.filbet2025.com' or self.config.get('API_URL') != 'https://client-fat.filbet2025.com':
            raise ValueError('pilot execution is authorized for FAT only')
        for case in cases:
            for step in case.get('steps',[]):
                scope = self.plan['contracts'][step['contract']].get('scope') if step['action']=='api' else 'kyc-review' if step['action']=='ui' else METHODS[step['method']]['scope']
                if scope and scope not in self.args.allow_write:
                    raise ValueError('selected case requires --allow-write ' + scope)
        if any(s['actor']=='B' or s.get('method')=='kyc_fixture' for c in cases for s in c.get('steps',[])):
            reviewer = self.config.get('QA_REVIEWER_ENV','.env.fat.reviewer.local')
            self.reviewer = {**self.config, **read_values(reviewer)}
            if self.reviewer.get('ADMIN_URL') != self.config['ADMIN_URL'] or self.reviewer['ADMIN_EMAIL'].lower() == self.config['ADMIN_EMAIL'].lower():
                raise ValueError('reviewer must be a distinct account on same service')

    def session(self, actor):
        if actor not in self.sessions:
            if actor == 'client': raise ValueError('client fixture not prepared')
            conf = self.reviewer if actor == 'B' else self.config
            session = Session(conf['ADMIN_URL'],conf,timeout=self.args.timeout,insecure=self.args.insecure)
            started = time.monotonic()
            session.login()
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
