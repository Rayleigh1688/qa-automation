"""Offline task confirmation → API evidence → manual import → renewed BUG review."""
import contextlib
import copy
import csv
from datetime import datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from support import ROOT
from qa_core.case_report import csv_text
from qa_core.team_delivery import MANUAL_FIELDS, prepare, import_results
from qa_core.execution_plan import load
from qa_delivery.requirement_bridge import task_plan
from qa_delivery.pipeline import run_pipeline, import_manual_review
from qa_delivery.state import Store, digest
from qa_delivery.intake import preview, confirm
from filbet.requirement_adapter import METHODS


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.story='ISOP-2027'
        self.req=self.root/'requirements'/self.story; self.req.mkdir(parents=True)
        for name in ('plan.json','design.md','questions.md','test-cases.md'):
            (self.req/name).write_bytes((ROOT/'requirements'/self.story/name).read_bytes())
        self.plan,self.cases,self.checksum=load(self.req/'plan.json',METHODS)
        self.config={'stories':{self.story:{'tester_id':2,'environments':['FAT'],
            'execution':{'case_ids':['review-list-state-1','2027-UI-001','2027-FLOW-001']}}},
            'environments':{'FAT':{'env_file':'.env.fat','version_probes':[]}}}
        self.payload={'story':self.story,'environment':'FAT','build':'build-17','scopes':['api','ui'],'tester_id':2}
        self.payload['execution']=task_plan(self.root,self.config,self.payload)
        self.state=self.root/'telegram'; self.folder=self.state/'runs/job1'
        self.store=Store(self.state/'queue.sqlite3'); self.addCleanup(self.store.close)
        with self.store.db:
            self.store.db.execute('INSERT INTO jobs(id,dedup,payload,status,config_hash) VALUES(?,?,?,?,?)',
                ('job1','job1',json.dumps(self.payload),'QUEUED',digest(self.config)))
        self.commands=[]
        self.root_patch=patch('qa_delivery.pipeline.ROOT',self.root); self.root_patch.start();self.addCleanup(self.root_patch.stop)

    def fake_api(self,argv,folder,name,*args):
        self.commands.append(argv)
        self.assertEqual(argv[1],'scripts/run-requirement.py')
        self.assertNotIn('2027-FLOW-001',argv);self.assertNotIn('2027-UI-001',argv)
        raw=self.root/'reports/qa'/self.story/'offline-run/result.json'; raw.parent.mkdir(parents=True)
        (raw.parent/'plan.snapshot.json').write_text(json.dumps(self.plan))
        report={'requirement':self.story,'environment':'FAT','mode':'execution','run_id':'offline-run',
            'source_time':datetime.now(timezone.utc).isoformat(),'deployment':argv[argv.index('--version')+1],
            'cases_sha256':self.checksum,'deployment_verification':{'status':'declared'},
            'results':[{'id':'review-list-state-1','status':'FAIL','actual':'offline fixture: expected list missing','evidence':str(raw)}]}
        raw.write_text(json.dumps(report))
        Path(argv[argv.index('--result-index')+1]).write_text(json.dumps({'raw':str(raw),'run_id':'offline-run'}))
        return 1

    def fake_ai(self,config,folder,phase,instruction,data,schema):
        return {'summary':'offline fixture review','bugs':[
            {'id':f'B{i+1}','case_id':r['id'],'category':'PRODUCT','title':'Fixture failure',
             'basis':'Confirmed fixture acceptance','steps':['Fixture step'],'expected':'Fixture expectation',
             'actual':r['detail'],'evidence':r['evidence']}
            for i,r in enumerate(x for x in data['results'] if x['status']=='FAIL')]}

    def run_job(self):
        with patch('qa_delivery.pipeline.command',side_effect=self.fake_api), patch('qa_delivery.pipeline.ai',side_effect=self.fake_ai):
            result=run_pipeline(self.config,self.store.get('job1'),self.folder)
        self.store.finish('job1',result)
        return result

    def fill_manual(self):
        filled=self.folder/'team-packet/manual.csv'
        with filled.open(encoding='utf-8-sig',newline='') as stream: rows=list(csv.DictReader(stream))
        proof=filled.parent/'proof.txt';proof.write_text('offline manual fixture, not live evidence')
        rows[0].update({'执行状态':'FAIL','实际结果':'offline fixture: message missing','证据':'proof.txt',
            '执行人':'offline tester','执行时间':datetime.now(timezone.utc).isoformat(),'未执行原因':''})
        filled.write_text(csv_text(rows,MANUAL_FIELDS))
        return filled

    def test_api_and_manual_failures_merge_without_replay_or_approval(self):
        initial=self.run_job(); old=self.store.get('job1')['revision']
        self.assertEqual(initial['status'],'FAIL',initial)
        statuses={r['id']:r['status'] for r in initial['results']}
        self.assertEqual(statuses['UI:2027-UI-001'],'NOT_RUN')
        self.assertEqual(statuses['API:2027-FLOW-001'],'NOT_RUN')
        self.assertEqual(initial['deployment_verification']['status'],'declared')
        with patch('qa_delivery.pipeline.ai',side_effect=self.fake_ai), patch('qa_delivery.pipeline.command') as command:
            new=import_manual_review(self.store,self.config,self.state,'job1',old,self.fill_manual())
            command.assert_not_called()
        merged=json.loads(self.store.get('job1')['report'])
        self.assertNotEqual(old,new);self.assertEqual(len(merged['bugs']),2)
        self.assertEqual(merged['results'][0],initial['results'][0])
        self.assertEqual(json.loads((self.folder/'initial-report.json').read_text()),initial)
        self.assertEqual(len(self.commands),1)
        with self.store.db:self.store._approve(['job1',old,'B1'],2,self.config)
        self.assertEqual(self.store.get('job1')['status'],'REVIEW')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM issues').fetchone()[0],0)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM outbox WHERE sent=0').fetchone()[0],0)
        with self.store.db:self.store._approve(['job1',new,'B1,B2'],2,self.config)
        self.assertEqual(self.store.get('job1')['status'],'APPROVED')
        with self.assertRaises(ValueError):import_manual_review(self.store,self.config,self.state,'job1',new,self.fill_manual())

    def test_confirmation_binds_plan_and_rejects_changed_plan_before_api(self):
        candidate={**self.payload,'issue':self.story,'text':self.story+' ready','message_id':1}
        with self.store.db:
            self.store.db.execute('INSERT INTO candidates VALUES(?,?,?)',('candidate1',json.dumps(candidate),'PENDING'))
        original=preview(self.store,self.config)
        self.plan['cases'][0]['review']['用例名称']+=' changed'
        (self.req/'plan.json').write_text(json.dumps(self.plan))
        with self.assertRaises(ValueError):confirm(self.store,self.config,['candidate1'],original['revision'])
        with patch('qa_delivery.pipeline.command') as command:
            result=run_pipeline(self.config,self.store.get('job1'),self.folder)
            command.assert_not_called()
        self.assertEqual(result['status'],'BLOCKED')
        # The file may change between selection validation and loading the packet.
        with patch('qa_delivery.requirement_bridge.task_plan',return_value=self.payload['execution']), \
             patch('qa_delivery.pipeline.command') as command:
            result=run_pipeline(self.config,self.store.get('job1'),self.state/'runs/raced-plan')
            command.assert_not_called()
        self.assertEqual(result['status'],'BLOCKED')

    def test_version_mismatch_source_rejected_and_redeploy_remains_blocked(self):
        def mismatch(argv,*args):
            code=self.fake_api(argv,*args)
            raw=self.root/'reports/qa'/self.story/'offline-run/result.json'
            data=json.loads(raw.read_text());data['deployment']='other';raw.write_text(json.dumps(data))
            return code
        with patch('qa_delivery.pipeline.command',side_effect=mismatch):
            result=run_pipeline(self.config,self.store.get('job1'),self.folder)
        self.assertEqual(result['status'],'BLOCKED');self.assertEqual(result['bugs'],[])

    def test_post_run_probe_failure_keeps_api_evidence_and_blocks_after_import(self):
        with patch('qa_delivery.pipeline.command',side_effect=self.fake_api), patch('qa_delivery.pipeline.check_version',side_effect=[True,ValueError('redeployed')]):
            result=run_pipeline(self.config,self.store.get('job1'),self.folder)
        self.assertEqual(result['status'],'BLOCKED')
        self.assertEqual(result['deployment_verification']['status'],'incomplete')
        revision=self.store.finish('job1',result)
        with patch('qa_delivery.pipeline.ai',side_effect=self.fake_ai):
            import_manual_review(self.store,self.config,self.state,'job1',revision,self.fill_manual())
        self.assertEqual(json.loads(self.store.get('job1')['report'])['status'],'BLOCKED')

    def test_import_rejects_changed_packet_or_api_evidence_without_replacing_review(self):
        self.run_job();old=self.store.get('job1')['report']; revision=self.store.get('job1')['revision']
        raw=self.root/'reports/qa'/self.story/'offline-run/result.json'
        raw.write_text(raw.read_text()+' ')
        with self.assertRaisesRegex(ValueError,'evidence changed'):
            import_manual_review(self.store,self.config,self.state,'job1',revision,self.fill_manual())
        self.assertEqual(self.store.get('job1')['report'],old)

    def test_manual_only_packet_does_not_launch_api_and_api_only_needs_no_manual_case(self):
        self.payload['scopes']=['ui'];self.payload['execution']=task_plan(self.root,self.config,self.payload)
        row={'payload':json.dumps(self.payload),'config_hash':digest(self.config)}
        with patch('qa_delivery.pipeline.command') as command:
            result=run_pipeline(self.config,row,self.folder);command.assert_not_called()
        self.assertEqual([r['id'] for r in result['results']],['UI:2027-UI-001'])
        only=[c for c in self.cases if c['id']=='review-list-state-1']
        packet=self.root/'api-only'
        prepare(self.plan,only,self.checksum,packet,'FAT','build-17')
        report=import_results(packet,packet/'manual.csv',self.root/'api-only-import')
        self.assertEqual(report['results'],[])

    def test_scope_defaults_do_not_execute_writes_or_ui(self):
        selection=self.payload['execution']
        self.assertEqual(selection['automatic_ids'],['review-list-state-1'])
        self.assertIn('2027-FLOW-001',selection['blocked'])
        self.config['stories'][self.story]['execution']['allow_write']=['kyc-review']
        selection=task_plan(self.root,self.config,self.payload)
        self.assertIn('2027-FLOW-001',selection['automatic_ids'])
        self.assertNotIn('2027-UI-001',selection['automatic_ids'])

    def test_legacy_ui_configuration_never_starts_browser(self):
        (self.req/'plan.json').unlink()
        self.payload['scopes']=['ui']
        self.config['stories'][self.story]['ui']={'FAT':{'pages':['legacy']}}
        row={'payload':json.dumps(self.payload),'config_hash':digest(self.config)}
        with patch('qa_delivery.pipeline.command') as command:
            result=run_pipeline(self.config,row,self.folder);command.assert_not_called()
        self.assertEqual(result['results'][0]['status'],'NOT_RUN')

    def test_approval_during_analysis_cannot_be_overwritten_by_manual_import(self):
        self.run_job();revision=self.store.get('job1')['revision']
        def approve_then_classify(*args):
            with self.store.db:self.store._approve(['job1',revision,'B1'],2,self.config)
            return self.fake_ai(*args)
        with patch('qa_delivery.pipeline.ai',side_effect=approve_then_classify):
            with self.assertRaisesRegex(ValueError,'review changed during import'):
                import_manual_review(self.store,self.config,self.state,'job1',revision,self.fill_manual())
        self.assertEqual(self.store.get('job1')['status'],'APPROVED')
        self.assertEqual(self.store.get('job1')['revision'],revision)

    def test_verified_version_requires_both_probes(self):
        self.config['environments']['FAT']['version_probes']=[{'url':'https://example.test/version','field':'build'}]
        row={'payload':json.dumps(self.payload),'config_hash':digest(self.config)}
        with patch('qa_delivery.pipeline.command',side_effect=self.fake_api),patch('qa_delivery.pipeline.ai',side_effect=self.fake_ai), \
             patch('qa_delivery.pipeline.request_json',return_value={'build':'build-17'}) as probe:
            result=run_pipeline(self.config,row,self.folder)
        self.assertEqual(result['deployment_verification']['status'],'verified')
        self.assertEqual(probe.call_count,2)

    def test_changed_packet_cannot_be_imported_even_with_valid_manual_rows(self):
        self.run_job();revision=self.store.get('job1')['revision']
        packet=self.folder/'team-packet/packet.json'
        packet.write_text(packet.read_text()+' ')
        with self.assertRaisesRegex(ValueError,'packet changed'):
            import_manual_review(self.store,self.config,self.state,'job1',revision,self.fill_manual())
        self.assertEqual(self.store.get('job1')['revision'],revision)

    def test_cli_version_is_declared_and_changed_plan_never_reaches_adapter(self):
        spec=importlib.util.spec_from_file_location('requirement_cli',ROOT/'scripts/run-requirement.py')
        cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli);cli.ROOT=self.root
        adapter=SimpleNamespace(environment='FAT',login_ms=0,preflight=Mock())
        argv=['qa',self.story,'--execute','--only','review-list-state-1','--version','build-17',
              '--expected-plan-sha256',self.checksum,'--result-index',str(self.root/'index.json')]
        with patch.object(sys,'argv',argv),patch('filbet.requirement_adapter.Adapter',return_value=adapter), \
             patch.object(cli,'execute',return_value=[{'id':'review-list-state-1','status':'PASS','actual':'offline fixture','steps':[]}]), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(),0)
        raw=Path(json.loads((self.root/'index.json').read_text())['raw'])
        report=json.loads(raw.read_text());self.assertEqual(report['deployment'],'build-17')
        self.assertEqual(report['deployment_verification']['status'],'declared')
        html=(raw.parent/'results.html').read_text()
        self.assertIn('build-17',html);self.assertIn('声明版本，未远程核验',html)
        argv=['qa',self.story,'--execute','--expected-plan-sha256','changed']
        with patch.object(sys,'argv',argv),patch('filbet.requirement_adapter.Adapter') as factory:
            with self.assertRaisesRegex(ValueError,'changed since confirmation'):cli.main()
            factory.assert_not_called()
