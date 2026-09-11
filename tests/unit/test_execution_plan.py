import copy
import unittest
from support import ROOT
from filbet.requirement_adapter import METHODS
from qa_core.execution_plan import load, validate, resolve, assertions, MISSING, at


class ExecutionPlanTests(unittest.TestCase):
    def setUp(self):
        self.plan, self.cases, _ = load(ROOT / 'requirements/ISOP-2027/plan.json', METHODS)

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
