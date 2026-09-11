import unittest
from support import ROOT
from qa_core.plan_runner import execute


class PlanRunnerTests(unittest.TestCase):
    def test_failure_stops_dependents_but_not_independent_case(self):
        class Adapter:
            def __init__(self): self.calls = []
            def execute(self, step, case_id):
                self.calls.append((case_id,step['id']))
                return {'http':200,'body':{'status':case_id!='bad'}}
        check = [{'path':'body.status','op':'eq','value':True}]
        step = {'id':'write','actor':'A','action':'api','expect':check}
        cases = [{'id':'bad','variables':{},'steps':[step,{**step,'id':'later'}]}, {'id':'good','variables':{},'steps':[step]}]
        adapter = Adapter()
        result = execute(cases,adapter,'offline')
        self.assertEqual([r['status'] for r in result],['FAIL','PASS'])
        self.assertEqual(adapter.calls,[('bad','write'),('good','write')])
        self.assertEqual(result[0]['steps'][1]['status'],'NOT_RUN')

    def test_transport_error_never_retries_write(self):
        class Adapter:
            calls = 0
            def execute(self, step, case_id):
                self.calls += 1
                raise TimeoutError('secret token must not be reported')
        adapter = Adapter()
        result = execute([{'id':'one','variables':{},'steps':[{'id':'write','actor':'A'}]}],adapter,'offline')
        self.assertEqual(adapter.calls,1)
        self.assertEqual(result[0]['status'],'ERROR')
        self.assertNotIn('secret token',str(result))

    def test_diagnostic_read_runs_after_failure_without_changing_failure(self):
        class Adapter:
            calls = []
            def execute(self,step,case_id):
                self.calls.append(step['id'])
                return {'http':200,'body':{'status':False}}
        adapter=Adapter()
        steps=[{'id':'write','actor':'A','expect':[{'path':'body.status','op':'eq','value':True}]},
               {'id':'snapshot','actor':'A','diagnostic':True}, {'id':'next-write','actor':'A'}]
        result=execute([{'id':'case','variables':{},'steps':steps}],adapter,'offline')
        self.assertEqual(adapter.calls,['write','snapshot'])
        self.assertEqual(result[0]['status'],'FAIL')
        self.assertEqual(result[0]['failed_step'],'write')
