import json
from pathlib import Path
import tempfile
import unittest
from qa_core.report_retention import retain_latest
from filbet.normal_profile import prepare_cases,reuse_ui
from types import SimpleNamespace
from unittest.mock import patch
from support import ROOT
from requirement_paths import requirement_dir, requirement_dirs

class ReportRetentionTests(unittest.TestCase):
    def test_keeps_latest_per_environment_and_identifiers(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)/'ISOP-2027';base.mkdir()
            def run(name,env,time):
                d=base/name;d.mkdir();(d/'result.json').write_text(json.dumps({'mode':'execution','environment':env,'source_time':time}));(d/'results.html').write_text('report');return d
            fat=run('fat','FAT','1');old=run('old','UAT','2');new=run('new','UAT','3')
            (old/'private-checkpoints.json').write_text(json.dumps([{'uid':'test-uid','token':'secret','case':'case'}]))
            (base/'unrelated').mkdir()
            self.assertEqual(retain_latest(new,state_dir=Path(tmp)/'state'),['old'])
            self.assertTrue(fat.exists());self.assertTrue(new.exists());self.assertTrue((base/'unrelated').exists())
            ledger=(Path(tmp)/'state/report-records-isop-2027.json').read_text();self.assertIn('test-uid',ledger);self.assertNotIn('secret',ledger)
            self.assertEqual(json.loads((base/'latest-fat.json').read_text())['run_id'],'fat')
    def test_incomplete_report_does_not_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'ISOP-2027/run';f.mkdir(parents=True)
            with self.assertRaises(ValueError):retain_latest(f,state_dir=Path(tmp)/'state')
            self.assertTrue(f.exists())
    def test_ui_reuse_rejects_changed_snapshot(self):
        a=SimpleNamespace(fixtures={'2027-UI-006':{'uid':'owned'}},normal_ui_pool=('2027-UI-006',{'processed':['one']}))
        with patch('filbet.normal_profile.snapshot_data',return_value={'processed':['changed']}):
            with self.assertRaises(RuntimeError):reuse_ui(a,{},'2027-UI-007')
        self.assertIsNone(a.normal_ui_pool)
    def test_ui_profile_preserves_actual_checks(self):
        original=[{'id':'2027-UI-007','steps':[{'id':'prepare'},{'id':'open-review'},{'id':'no-approve'}]}]
        selected=prepare_cases(original)
        self.assertEqual([s['id'] for s in selected[0]['steps']],['reuse-processed','open-review','no-approve'])
        self.assertEqual(original[0]['steps'][0]['id'],'prepare')
    def test_real_shared_ui_queries_resolve_processed_record_id(self):
        from qa_core.execution_plan import load,resolve
        from filbet.requirement_adapter import METHODS
        _,cases,_=load(requirement_dir(ROOT, 'ISOP-2027') / 'plan.json',METHODS)
        for case in prepare_cases(cases):
            if case['id'] not in {f'2027-UI-{i:03}' for i in range(7,14)}:
                continue
            variables={'fixture':{'uid':'owned'},'processed':{'processed':[{'id':'owned-record'}]}}
            for step in case['steps'][1:]:
                resolved=resolve(step,variables)
                if step['id']=='search':
                    assertion=next(x for x in resolved['expect'] if x['path']=='body.data.d.0.id')
                    self.assertEqual(assertion['value'],'owned-record')

    def test_corrected_scope_does_not_drop_security_or_missing_implementations(self):
        profile=json.loads((requirement_dir(ROOT, 'ISOP-2027') / 'regression-profile.json').read_text())
        from qa_core.execution_plan import load
        from filbet.requirement_adapter import METHODS
        _,cases,_=load(requirement_dir(ROOT, 'ISOP-2027') / 'plan.json',METHODS)
        selected=set(profile['cases']);deferred={x['id'] for x in profile['deferred']}
        self.assertFalse(selected & deferred)
        self.assertEqual(selected|deferred,{c['id'] for c in cases})
        for ident in ['2027-API-004','2027-API-015','2027-API-019','2027-API-030','2027-UI-015','auth-missing']:
            self.assertIn(ident,selected)
        self.assertIn('2027-API-002',deferred)

    def test_missing_review_grant_blocks_self_review_instead_of_passing(self):
        from filbet.normal_profile import apply_role_preconditions
        session=SimpleNamespace(request=lambda method,path,**kwargs: {'body':{'status':True,'data':{'group_id':'role'} if path.endswith('detail') else {'d':[{'gid':'role','name':'Codex','permission':'["20001"]'}]}}})
        adapter=SimpleNamespace(session=lambda actor:session)
        cases=[{'id':'self-review','steps':[{'actor':'B','contract':'review'}]},
               {'id':'independent','steps':[{'actor':'A','contract':'review'}]}]
        result=apply_role_preconditions(adapter,cases)
        self.assertEqual(result['blocked_cases'],['self-review'])
        self.assertNotIn('blocked',cases[1])
