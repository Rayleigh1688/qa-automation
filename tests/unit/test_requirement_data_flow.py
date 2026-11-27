import copy
from contextlib import nullcontext, redirect_stdout
import io
import json
from pathlib import Path
import runpy
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from support import ROOT
from filbet.requirement_adapter import Adapter, METHODS
from qa_core.case_report import FIELDS
from qa_core.execution_plan import validate
from qa_core.plan_runner import execute


def step(name, contract, *, actor='member', checks=(), **options):
    return {'id': name, 'action': 'api', 'actor': actor, 'contract': contract, **options,
            'expect': [{'path': 'http', 'op': 'eq', 'value': 200},
                       {'path': 'body.status', 'op': 'eq', 'value': True}, *checks]}


def definition(case_id, steps, *, datasets=()):
    row = {**dict.fromkeys(FIELDS, 'offline fixture'), '用例编号': case_id,
           '类型': 'FLOW' if len(steps) > 1 else 'API', '验收点': 'A01'}
    case = {'id': case_id, 'review': row, 'steps': steps}
    if datasets:
        case['datasets'] = list(datasets)
    return case


def fixture_plan():
    return {
        'schema_version': 2, 'requirement': 'ISOP-2375', 'acceptance_ids': ['A01'],
        'services': {'client': {'env': 'API_URL'}},
        'actors': {'member': {'services': ['client'], 'session': 'client_password'},
                   'visitor': {'services': ['client'], 'session': 'anonymous'}},
        'contracts': {name: {'service': 'client', 'method': 'GET', 'encoding': 'cbor',
                             'path': '/fixture/' + name, 'write': False}
                      for name in ('wallet', 'order', 'ledger', 'public')},
        'datasets': {'deposit': {'order': 'deposit-017', 'amount': '10.25', 'page': 2}},
        'cases': [definition('FLOW', [
            step('before', 'wallet', checks=[{'path': 'body.data.balance', 'op': 'eq', 'value': '100.50'}],
                 extract={'before_balance': 'body.data.balance'}),
            step('settled', 'order', query={'page': '${data.page}'}, checks=[
                {'path': 'body.data.id', 'op': 'eq', 'value': '${data.order}'},
                {'path': 'body.data.amount', 'op': 'eq', 'value': '${data.amount}'},
                {'path': 'body.data.state', 'op': 'eq', 'value': 'settled'},
            ], extract={'order_id': 'body.data.id', 'credited_amount': 'body.data.amount'}),
            step('ledger', 'ledger', query={'order_id': '${order_id}'}, checks=[
                {'path': 'body.data.order_id', 'op': 'eq', 'value': '${order_id}'}]),
            step('balance', 'wallet', checks=[{'path': 'body.data.balance', 'op': 'decimal_delta',
                 'value': {'before': '${before_balance}', 'change': '${credited_amount}'}}]),
        ], datasets=['deposit']), definition('GUEST', [step('public', 'public', actor='visitor')])],
    }


class DataFlowTests(unittest.TestCase):
    def run_fixture(self, *, sign_in=True, settled=True):
        calls = []

        def respond(request, timeout):
            url = urlsplit(request.full_url)
            auth = dict((name.lower(), value) for name, value in request.header_items()).get('t')
            query = parse_qs(url.query)
            calls.append((request.method, url.path, query, auth))
            body = {'status': True}
            if url.path == '/member/v2/login':
                body = {'status': sign_in, 'data': 'fixture-secret-token' if sign_in else None}
            elif url.path == '/fixture/wallet':
                body['data'] = {'balance': '100.50' if len(calls) == 2 else '110.75'}
            elif url.path == '/fixture/order':
                body['data'] = {'id': 'deposit-017', 'amount': '10.25', 'state': 'settled' if settled else 'pending'}
            elif url.path == '/fixture/ledger':
                body['data'] = {'order_id': query.get('order_id', [None])[0]}
            response = io.BytesIO(json.dumps(body).encode())
            response.code = 200
            return response

        plan = fixture_plan()
        cases = validate(plan, METHODS)
        config = {'API_URL': 'https://fixture.invalid', 'CLIENT_PHONE': 'fixture-member',
                  'CLIENT_PASSWORD': 'fixture-password'}
        with patch('filbet.requirement_adapter.load_environment', return_value=config), \
             patch('filbet.requirement_session.build_opener', return_value=SimpleNamespace(open=respond)):
            adapter = Adapter(plan, SimpleNamespace(env='.env.fat', timeout=1, insecure=False), ROOT)
            results = execute(cases, adapter, 'offline')
        return results, calls

    def test_session_and_extracted_values_pass_to_dependents(self):
        results, calls = self.run_fixture()
        self.assertEqual([case['status'] for case in results], ['PASS', 'PASS'])
        self.assertEqual(calls[0], ('POST', '/member/v2/login', {}, None))
        self.assertEqual(calls[2][2], {'page': ['2']})
        self.assertEqual(calls[3][2], {'order_id': ['deposit-017']})
        self.assertEqual([entry[3] for entry in calls[1:]], ['fixture-secret-token'] * 4 + [None])
        self.assertNotIn('fixture-secret-token', str(results))
        self.assertNotIn('deposit-017', str(results))

    def test_failed_order_stops_follow_up_but_keeps_independent_case(self):
        results, calls = self.run_fixture(settled=False)
        self.assertEqual([case['status'] for case in results], ['FAIL', 'PASS'])
        self.assertEqual([entry[1] for entry in calls], ['/member/v2/login', '/fixture/wallet', '/fixture/order', '/fixture/public'])
        self.assertEqual([s['status'] for s in results[0]['steps']], ['PASS', 'FAIL', 'NOT_RUN', 'NOT_RUN'])

    def test_failed_sign_in_skips_protected_requests(self):
        results, calls = self.run_fixture(sign_in=False)
        self.assertEqual([case['status'] for case in results], ['ERROR', 'PASS'])
        self.assertEqual([entry[1] for entry in calls], ['/member/v2/login', '/fixture/public'])

    def test_read_only_member_login_failure_does_not_block_unrelated_kyc_fixture(self):
        with patch('filbet.requirement_adapter.load_environment', return_value={}):
            adapter = Adapter(fixture_plan(), SimpleNamespace(env='.env.fat'), ROOT)
        unrelated = {'steps': [{'actor': 'A', 'method': 'kyc_fixture'}]}
        adapter.login_failed_actors.add('member')
        self.assertFalse(adapter.case_blocker(unrelated))
        adapter.login_failed_actors.add('B')
        self.assertTrue(adapter.case_blocker(unrelated))

    def test_client_session_requires_a_read_only_contract_and_matching_auth(self):
        plan = fixture_plan()
        with_login_on_anonymous = copy.deepcopy(plan)
        with_login_on_anonymous['cases'][1]['steps'][0]['auth'] = 'valid'
        with self.assertRaisesRegex(ValueError, 'matching auth and a read-only contract'):
            validate(with_login_on_anonymous, METHODS)
        plan['contracts']['order'].update(write=True, scope='fixture-write')
        with self.assertRaisesRegex(ValueError, 'matching auth and a read-only contract'):
            validate(plan, METHODS)

    def test_client_only_fat_preflight_defaults_client_host_without_admin_host(self):
        plan = fixture_plan()
        cases = validate(plan, METHODS)
        args = SimpleNamespace(env='.env.fat', allow_write=[])
        with patch('filbet.requirement_adapter.load_environment', return_value={}), \
             patch('filbet.requirement_adapter.Session') as session:
            adapter = Adapter(plan, args, ROOT)
            adapter.preflight(cases)
        self.assertEqual(adapter.environment, 'FAT')
        self.assertEqual(adapter.config['API_URL'], 'https://client-fat.filbet2025.com')
        self.assertNotIn('ADMIN_URL', adapter.config)
        session.assert_not_called()

    def test_client_only_preflight_does_not_bypass_environment_guards(self):
        plan = fixture_plan()
        cases = validate(plan, METHODS)
        mixed_plan = copy.deepcopy(plan)
        mixed_plan['services']['admin'] = {'env': 'ADMIN_URL'}
        for selected, env, config, error in (
            (plan, '.env.uat', {}, 'UAT selection cannot use FAT endpoints'),
            (plan, '.env.fat', {'API_URL': 'https://fixture.invalid'}, 'unsupported or mixed'),
            (mixed_plan, '.env.fat', {'API_URL': 'https://client-fat.filbet2025.com'}, 'unsupported or mixed'),
        ):
            with self.subTest(env=env, config=config, services=selected['services']), \
                 patch('filbet.requirement_adapter.load_environment', return_value=config):
                adapter = Adapter(selected, SimpleNamespace(env=env, allow_write=[]), ROOT)
                with self.assertRaisesRegex(ValueError, error):
                    adapter.preflight(cases)

    def test_withdraw_credentials_are_bound_only_to_designated_member_session(self):
        plan = fixture_plan()
        plan['actors']['wallet_member'] = {
            'services': ['client'], 'session': 'client_password', 'credentials': 'withdraw_client',
        }
        validate(plan, METHODS)
        config = {'API_URL': 'https://client-fat.filbet2025.com',
                  'CLIENT_PHONE': 'ordinary-test', 'CLIENT_PASSWORD': 'ordinary-test-password',
                  'WITHDRAW_CLIENT_PHONE': 'withdraw-test', 'WITHDRAW_CLIENT_PASSWORD': 'withdraw-test-password'}
        args = SimpleNamespace(env='.env.fat', timeout=1, insecure=False)
        with patch('filbet.requirement_adapter.load_environment', return_value=config), \
             patch('filbet.requirement_adapter.Session') as session:
            adapter = Adapter(plan, args, ROOT)
            adapter.session('wallet_member')
            adapter.session('member')

        wallet_config = session.call_args_list[0].args[1]
        member_config = session.call_args_list[1].args[1]
        self.assertEqual(wallet_config['CLIENT_PHONE'], config['WITHDRAW_CLIENT_PHONE'])
        self.assertEqual(wallet_config['CLIENT_PASSWORD'], config['WITHDRAW_CLIENT_PASSWORD'])
        self.assertEqual(member_config['CLIENT_PHONE'], 'ordinary-test')
        self.assertEqual(member_config['CLIENT_PASSWORD'], 'ordinary-test-password')

    def test_withdraw_credentials_do_not_fall_back_to_normal_member(self):
        plan = fixture_plan()
        plan['actors']['member']['credentials'] = 'withdraw_client'
        config = {'CLIENT_PHONE': 'ordinary-test', 'CLIENT_PASSWORD': 'ordinary-test-password'}
        with patch('filbet.requirement_adapter.load_environment', return_value=config), \
             patch('filbet.requirement_adapter.Session') as session:
            adapter = Adapter(plan, SimpleNamespace(env='.env.fat'), ROOT)
            with self.assertRaisesRegex(ValueError, 'requires WITHDRAW_CLIENT_PHONE and WITHDRAW_CLIENT_PASSWORD'):
                adapter.session('member')
        session.assert_not_called()

    def test_actor_rejects_unsupported_credentials(self):
        for actor, credential in (('visitor', 'withdraw_client'), ('member', 'unknown'), ('member', None)):
            with self.subTest(actor=actor, credential=credential):
                plan = fixture_plan()
                plan['actors'][actor]['credentials'] = credential
                with self.assertRaisesRegex(ValueError, 'unsupported client actor credentials'):
                    validate(plan, METHODS)


class RequirementApiPresetTests(unittest.TestCase):
    story = 'ISOP-900000'

    def write_plan(self, root, *, write=False):
        folder = root / 'requirements' / self.story
        (folder / 'api').mkdir(parents=True)
        plan = fixture_plan()
        plan.update(requirement=self.story,
                    actors={'visitor': {'services': ['client']}},
                    cases_file='api/test-cases.json',
                    datasets={'first': {'page': 1}, 'second': {'page': 2}})
        if not write:
            plan['actors']['visitor']['session'] = 'anonymous'
        contracts = {'public': {**plan.pop('contracts')['public'], 'method': 'POST',
                                'encoding': 'json', 'write': write}}
        if write:
            contracts['public']['scope'] = 'fixture-write'
        request = step(
            'list', 'public', actor='visitor', body={'page': '${data.page}'},
            checks=[{'path': 'body.data.page', 'op': 'eq', 'value': '${data.page}'}],
        )
        cases = [definition('API-01', [request], datasets=('first', 'second'))]
        del plan['cases']
        (folder / 'plan.json').write_text(json.dumps(plan), encoding='utf-8')
        (folder / plan['cases_file']).write_text(json.dumps({'contracts': contracts, 'cases': cases}), encoding='utf-8')

    def invoke(self, root, *args):
        path = ROOT / 'scripts/run-requirement.py'
        main = runpy.run_path(str(path))['main']
        output = io.StringIO()
        with patch.dict(main.__globals__, ROOT=root, local_run_lock=nullcontext), \
             patch.object(sys, 'argv', [str(path), self.story, '--fat-api', *args]), redirect_stdout(output):
            return main(), output.getvalue()

    def test_new_requirement_runs_from_plan_and_data_without_new_runner(self):
        pages = []
        messages = [
            {'id': index, 'title': f'弹窗样本 {index}', 'body_text': '<em>原样文本</em>',
             'status': 1, **{f'field_{column}': column for column in range(16)}}
            for index in range(1, 152)
        ]

        def respond(request, timeout):
            self.assertEqual((request.method, urlsplit(request.full_url).path), ('POST', '/fixture/public'))
            page = json.loads(request.data)['page']
            pages.append(page)
            response = io.BytesIO(json.dumps({
                'status': True, 'data': {'page': page, 'messages': messages},
            }).encode())
            response.code = 200
            return response

        with tempfile.TemporaryDirectory() as temp, \
             patch('filbet.requirement_adapter.load_environment', return_value={}), \
             patch('filbet.requirement_session.build_opener', return_value=SimpleNamespace(open=respond)):
            root = Path(temp)
            self.write_plan(root)
            self.assertIn('validated 2 cases; executable 2; no login', self.invoke(root)[1])
            self.assertEqual(pages, [])
            code, output = self.invoke(root, '--execute')
            self.assertEqual(code, 0)
            self.assertEqual(pages, [1, 2])
            folder = root / 'reports/qa' / self.story
            pointer = json.loads((folder / 'latest.json').read_text())
            report = json.loads((folder / pointer['raw']).read_text())
            self.assertEqual([row['id'] for row in report['results']], ['API-01:first', 'API-01:second'])
            html = (folder / pointer['results']).read_text(encoding='utf-8')
            self.assertIn('响应正文', html)
            self.assertIn('&quot;id&quot;: 151', html)
            self.assertIn('弹窗样本 151', html)
            self.assertIn('&quot;field_15&quot;: 15', html)
            self.assertIn('&lt;em&gt;原样文本&lt;/em&gt;', html)
            self.assertNotIn('hidden key', html)
            self.assertNotIn('弹窗样本 151', json.dumps(report, ensure_ascii=False))
            self.assertNotIn('弹窗样本 151', output)

            index = root / 'orchestration.json'
            self.assertEqual(self.invoke(root, '--execute', '--result-index', str(index))[0], 0)
            indexed = Path(json.loads(index.read_text())['raw'])
            orchestrated_html = indexed.with_name('results.html').read_text(encoding='utf-8')
            self.assertIn('响应预览（已脱敏）', orchestrated_html)
            self.assertNotIn('弹窗样本 151', orchestrated_html)

    def test_preset_rejects_write_steps_and_other_environments_before_adapter(self):
        with tempfile.TemporaryDirectory() as temp, patch('filbet.requirement_adapter.Adapter') as adapter:
            root = Path(temp)
            self.write_plan(root, write=True)
            with self.assertRaisesRegex(ValueError, 'requires read-only API steps'):
                self.invoke(root, '--execute')
            with self.assertRaisesRegex(ValueError, 'requires .env.fat'):
                self.invoke(root, '--execute', '--env', '.env.uat')
            adapter.assert_not_called()
