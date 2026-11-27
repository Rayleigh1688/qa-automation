import copy
import unittest
from support import ROOT
from requirement_paths import requirement_dir, requirement_dirs
from filbet.requirement_adapter import METHODS
from qa_core.execution_plan import load, validate, resolve, assertions, MISSING, at


class ExecutionPlanTests(unittest.TestCase):
    def setUp(self):
        self.plan, self.cases, _ = load(requirement_dir(ROOT, 'ISOP-2027') / 'plan.json', METHODS)

    def test_historical_ids_preserved(self):
        self.assertTrue({'2027-FLOW-001', '2027-API-001', 'review-list-state-1'} <= {c['id'] for c in self.cases})

    def test_invalid_plans_rejected_offline(self):
        for mutation in ('duplicate', 'actor', 'action', 'assertion', 'reference', 'contract'):
            with self.subTest(mutation=mutation):
                p = copy.deepcopy(self.plan)
                c = next(c for c in p['cases'] if c.get('steps'))
                s = next(s for s in c['steps'] if s['action'] == 'api')
                if mutation == 'duplicate': p['cases'].append(copy.deepcopy(c))
                if mutation == 'actor': s['actor'] = 'unknown'
                if mutation == 'action': s['action'] = 'eval'
                if mutation == 'assertion': s['expect'] = []
                if mutation == 'reference': s['body'] = {'id': '${unknown.id}'}
                if mutation == 'contract': s['contract'] = 'unknown'
                with self.assertRaises(ValueError): validate(p, METHODS)

    def test_types_large_integer_and_missing_null(self):
        uid = 9223372036854775807
        self.assertEqual(resolve('${uid}', {'uid': uid}), uid)
        self.assertIs(type(resolve('${uid}', {'uid': uid})), int)
        self.assertIs(at({}, 'id'), MISSING)
        checks = [{'path':'body.id','op':'eq','value':None}]
        self.assertEqual(assertions(checks, {'body':{}})[0]['status'], 'FAIL')
        self.assertEqual(assertions(checks, {'body':{'id':None}})[0]['status'], 'PASS')
        self.assertEqual(assertions([{'path':'body.id','op':'type','value':'integer'}], {'body':{'id':True}})[0]['status'], 'FAIL')

    def test_business_failure_and_empty_set_not_pass(self):
        checks = [{'path':'http','op':'eq','value':200},{'path':'body.status','op':'eq','value':True},{'path':'body.data','op':'nonempty'}]
        got = assertions(checks, {'http':200,'body':{'status':False,'data':[]}})
        self.assertEqual([r['status'] for r in got], ['PASS','FAIL','FAIL'])

    def test_dataset_ids_and_forward_extract(self):
        p = copy.deepcopy(self.plan)
        c = next(c for c in p['cases'] if c.get('steps'))
        p['cases'] = [c]
        p['datasets'] = {'empty':{'value':None},'large':{'value':9223372036854775807}}
        c['datasets'] = ['empty','large']
        c['steps'][0]['query'] = {'uid':'${data.value}'}
        self.assertEqual(len(validate(p, METHODS)), 2)
        c['steps'][0]['query'] = {'uid':'${later}'}
        c['steps'][0]['extract'] = {'later':'body.data.id'}
        with self.assertRaises(ValueError): validate(p, METHODS)

    def test_fixture_dataset_invalid_state_rejected_before_login(self):
        p = copy.deepcopy(self.plan)
        p['datasets']['kyc-state-3']['status'] = 'unconfirmed'
        with self.assertRaises(ValueError): validate(p, METHODS)

    def test_sample_assertion_requires_typed_fields_in_the_same_row(self):
        check = {'path': 'body.data', 'op': 'any_row_matches', 'value': {'id': 17, 'bank.code': 'TEST'}}
        for rows, expected in (
            ([{'id': 17, 'bank': {'code': 'TEST'}, 'name': 'fixture'}], 'PASS'),
            ([{'id': '17', 'bank': {'code': 'TEST'}}], 'FAIL'),
            ([{'id': 17}, {'bank': {'code': 'TEST'}}], 'FAIL'),
            ([], 'FAIL'),
        ):
            with self.subTest(rows=rows):
                self.assertEqual(assertions([check], {'body': {'data': rows}})[0]['status'], expected)

    def test_recursive_field_assertion_distinguishes_missing_blank_and_wrong_type(self):
        check = {'path': 'body.data', 'op': 'fields_absent_or', 'value': {'updated_uid': [0], 'maintainer': []}}
        body = {'data': {'list': [{'updated_uid': 0}, {}]}}
        self.assertEqual(assertions([check], {'body': body})[0]['status'], 'PASS')
        body['data']['list'].append({'extra': [{'updated_uid': False, 'maintainer': 'private-fixture'}]})
        result = assertions([check], {'body': body})[0]
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['unexpected_fields'], ['maintainer', 'updated_uid'])
        self.assertNotIn('private-fixture', str(result))
        self.assertEqual(assertions([check], {'body': {'data': None}})[0]['status'], 'FAIL')
        self.assertEqual(assertions([check], {'body': {}})[0]['status'], 'FAIL')

    def test_decimal_delta_uses_exact_amount_and_rejects_invalid_types(self):
        before = '20000000000000000000000000000.01'
        check = {'path': 'body.balance', 'op': 'decimal_delta', 'value': {'before': before, 'change': '0.02'}}
        for actual, expected in (
            ('20000000000000000000000000000.03', 'PASS'),
            ('20000000000000000000000000000.04', 'FAIL'),
            (True, 'FAIL'),
            ('NaN', 'FAIL'),
        ):
            with self.subTest(actual=actual):
                self.assertEqual(assertions([check], {'body': {'balance': actual}})[0]['status'], expected)
