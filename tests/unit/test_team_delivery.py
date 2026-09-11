"""Prevent manual false passes, edited contracts, source collisions and UI result substitution."""
import copy
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from support import ROOT
from qa_core.case_report import FIELDS, csv_text
from qa_core.execution_plan import expand
from qa_core.team_delivery import MANUAL_FIELDS, prepare, import_results, select_automatic


def case(key, manual=False):
    row=dict(zip(FIELDS,[key,'UI' if manual else 'API','Example','Check','Fixture','Action','Expected','冒烟','C01']))
    return {'id':key,'review':row,'steps':[{'id':'check','actor':'A','action':'ui' if manual else 'api'}],
        'delivery':{'mode':'manual','precondition':'本轮样本','steps':'点击并查看提示','expected':'提示正确'} if manual else {'mode':'automatic'}}


class TeamDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.plan={'requirement':'ISOP-2027','contracts':{},'cases':[case('A'),case('M',True)]}
        self.cases=expand(self.plan)
        self.packet=self.root/'packet';self.filled=self.packet/'manual.csv'
        prepare(self.plan,self.cases,'original-plan-digest',self.packet,'FAT','未提供')

    def tearDown(self): self.temp.cleanup()

    def rows(self):
        with self.filled.open(encoding='utf-8-sig',newline='') as stream:return list(csv.DictReader(stream))

    def save(self,rows):self.filled.write_text(csv_text(rows,MANUAL_FIELDS))

    def completed(self):
        rows=self.rows();(self.packet/'proof.txt').write_text('offline fixture evidence; not a real UI run')
        rows[0].update({'执行状态':'PASS','实际结果':'提示正确（本地测试夹具）','证据':'proof.txt','执行人':'offline tester',
            '执行时间':datetime.now(timezone.utc).isoformat(),'未执行原因':''})
        return rows

    def auto(self, name='auto', **changes):
        folder=self.root/name;folder.mkdir()
        (folder/'plan.snapshot.json').write_text(json.dumps(self.plan))
        report={'mode':'execution','run_id':name,'source_time':'2026-09-11T00:00:00+00:00','environment':'FAT',
            'results':[{'id':'A','status':'FAIL','actual':'offline API rejection','evidence':'old'},
                       {'id':'M','status':'PASS','actual':'old UI automatic result','evidence':'old'}]}
        report.update(changes);(folder/'result.json').write_text(json.dumps(report))
        return folder/'result.json'

    def test_blank_manual_stays_not_run_old_ui_pass_not_substituted(self):
        result=import_results(self.packet,self.filled,self.root/'out',[self.auto()])
        self.assertEqual([(r['id'],r['status']) for r in result['results']],[('A','FAIL'),('M','NOT_RUN')])
        self.assertEqual(result['sources'][0]['excluded_ids'],['M'])
        self.assertEqual(select_automatic(self.cases),[self.cases[0]])
        self.assertIn('本次导入未执行测试',(self.root/'out/results.html').read_text())
        self.assertFalse((self.root/'latest.json').exists())
        for folder in [self.packet, self.root/'out']:
            self.assertTrue((folder/'results.csv').is_file())
            for name in ['cases.csv','failures.csv','pending.csv','summary.json']:
                self.assertFalse((folder/name).exists())

    def test_completed_manual_requires_provenance_and_preserves_input(self):
        self.save(self.completed());before=self.filled.read_bytes()
        result=import_results(self.packet,self.filled,self.root/'out')
        self.assertEqual(result['results'][0]['status'],'PASS')
        self.assertEqual(result['results'][0]['execution_method'],'manual')
        self.assertEqual(self.filled.read_bytes(),before)
        self.assertEqual((self.root/'out/manual-import.csv').read_bytes(),before)
        with self.assertRaises(ValueError):import_results(self.packet,self.filled,self.root/'out')

    def test_missing_or_fabricated_execution_metadata_rejected(self):
        original=self.completed()
        for key in ['实际结果','证据','执行人','执行时间']:
            rows=copy.deepcopy(original);rows[0][key]='';self.save(rows)
            with self.assertRaises(ValueError):import_results(self.packet,self.filled,self.root/'out')
        for changes in [{'未执行原因':'待人工执行'},{'执行状态':'DONE'}, {'执行时间':'2026-01-01T00:00:00'},
                        {'证据':'missing.png'},{'证据':'javascript:alert(1)'},{'批次':'another'}, {'预期结果':'changed'}, {'环境':'UAT'}]:
            rows=copy.deepcopy(original);rows[0].update(changes);self.save(rows)
            with self.assertRaises(ValueError):import_results(self.packet,self.filled,self.root/'out')
        self.assertFalse((self.root/'out').exists())

    def test_duplicate_missing_and_unknown_rows_rejected(self):
        original=self.rows()
        for rows in [[],original*2,[{**original[0],'用例编号':'unknown'}]]:
            self.save(rows)
            with self.assertRaises(ValueError):import_results(self.packet,self.filled,self.root/'out')

    def test_auto_conflict_environment_and_contract_change_rejected(self):
        one=self.auto()
        with self.assertRaises(ValueError):import_results(self.packet,self.filled,self.root/'out',[one,one])
        with self.assertRaises(ValueError):import_results(self.packet,self.filled,self.root/'out',[self.auto('uat',environment='UAT')])
        with self.assertRaises(ValueError):import_results(self.packet,self.filled,self.root/'out',[self.auto('history',mode='historical-summary')])
        changed=copy.deepcopy(self.plan);changed['cases'][0]['steps'][0]['id']='different'
        (one.parent/'plan.snapshot.json').write_text(json.dumps(changed))
        with self.assertRaises(ValueError):import_results(self.packet,self.filled,self.root/'out',[one])

    def test_packet_source_change_rejected(self):
        (self.packet/'plan.snapshot.json').write_text('{}')
        with self.assertRaises(ValueError):import_results(self.packet,self.filled,self.root/'out')

    def test_manual_only_case_validates_and_cannot_become_automatic_pass(self):
        from qa_core.execution_plan import validate
        from qa_core.plan_runner import execute
        from filbet.requirement_adapter import METHODS
        plan=json.loads((ROOT/'requirements/ISOP-2027/plan.json').read_text())
        row=next(c for c in plan['cases'] if c['id']=='2027-UI-001')
        row.pop('steps');plan['cases']=[row]
        cases=validate(plan,METHODS)
        class NoExecution:
            def execute(self,*args): raise AssertionError('manual case must not execute')
        result=execute(cases,NoExecution(),'offline')
        self.assertEqual(result[0]['status'],'NOT_RUN')
        row.pop('delivery')
        with self.assertRaises(ValueError):validate(plan,METHODS)
