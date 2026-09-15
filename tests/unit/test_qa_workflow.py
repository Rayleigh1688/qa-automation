"""Offline verification of source history, isolated status edits, and execution guards."""
import copy
import os
import json
import tempfile
import subprocess
import threading
import unittest
import urllib.request
import urllib.error
from http.server import HTTPServer
from pathlib import Path
from unittest.mock import Mock, patch
from support import ROOT
from qa_delivery.state import digest
from qa_workflow.state import State, collect_results
from qa_workflow.generation import generate, validate, context
from qa_workflow.service import preflight, process_candidates, event_reason
from qa_workflow.web import handler, render
from qa_delivery.pipeline import render_report


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'requirements').mkdir()
        (self.root/'config').mkdir()
        for name in ('status-seed.json',):
            (self.root/'requirements'/name).write_bytes((ROOT/'requirements'/name).read_bytes())
        (self.root/'config/workflow.json').write_bytes((ROOT/'config/workflow.json').read_bytes())
        (self.root/'scripts/qa_workflow').mkdir(parents=True)
        (self.root/'scripts/qa_workflow/status-template.html').write_bytes((ROOT/'scripts/qa_workflow/status-template.html').read_bytes())
        self.state = State(self.root)
        self.addCleanup(self.state.close)
        self.story = 'ISOP-2028'
        dest = self.root/'requirements'/self.story
        dest.mkdir()
        for name in ('plan.json','design.md','questions.md','test-cases.md'):
            (dest/name).write_bytes((ROOT/'requirements'/self.story/name).read_bytes())
        self.config = {'stories':{self.story:{'environments':['FAT']}},'environments':{'FAT':{'env_file':'.env.fat'}}}

    def edit(self, channel='ui', base=0):
        return {'channel':channel,'status':'通过','author':'测试人','source':'本地人工批次','reason':'FAT指定范围','base_revision':base}

    def test_manual_persistence_conflict_and_automatic_failure_are_independent(self):
        self.state.append(self.story,'automatic',{'status':'FAIL','source':'first-run'})
        self.state.manual(self.story,self.edit())
        self.state.manual(self.story,self.edit('api'))
        other = State(self.root)
        try:
            row = next(r for r in other.view()['requirements'] if r['story']==self.story)
            self.assertEqual(row['automatic'][0]['status'],'FAIL')
            self.assertEqual(row['manual']['ui']['status'],'通过')
            with self.assertRaisesRegex(ValueError,'其他窗口'): other.manual(self.story,self.edit())
            revision = row['manual']['ui']['revision']
            other.manual(self.story,{**self.edit(base=revision),'status':'待复验'})
            row = next(r for r in other.view()['requirements'] if r['story']==self.story)
            self.assertEqual(len(row['history']),4)
            self.assertEqual(row['manual']['ui']['supersedes'],revision)
        finally: other.close()

    def test_event_claim_dedup_survives_restart(self):
        self.assertTrue(self.state.claim('event',{}))
        other = State(self.root)
        try: self.assertFalse(other.claim('event',{}))
        finally: other.close()
        self.state.finish('event','INTERRUPTED')
        self.assertFalse(self.state.claim('event',{}))

    def test_paused_and_uat_cannot_reach_business_preflight(self):
        with patch('qa_workflow.service.Adapter') as adapter:
            p = preflight(self.state,self.config,'ISOP-2022')
            self.assertEqual(p['status'],'BLOCKED')
            self.assertTrue(any('暂停' in r for r in p['reasons']))
            self.assertEqual(preflight(self.state,self.config,self.story,'UAT')['status'],'BLOCKED')
            adapter.assert_not_called()

    def test_changed_plan_is_blocked(self):
        p = self.root/'requirements'/self.story/'plan.json'
        p.write_text(p.read_text()+'\n')
        with patch('qa_workflow.service.Adapter') as adapter:
            result = preflight(self.state,self.config,self.story)
            self.assertTrue(any('计划' in reason for reason in result['reasons']))
            adapter.assert_not_called()

    def candidate(self):
        return {'id':'c1','story':self.story,'issues':[self.story],'member_ids':['c1'],'environment':'FAT','build':'v1','scopes':['api'],
            'source_messages':[{'action':'READY','environment_source':'AI evidence','text':'FAT 后端接口提测','scope_note':'API'}]}

    def test_event_default_environment_and_ui_do_not_trigger(self):
        c = self.candidate()
        c['source_messages'][0]['environment_source']='local default; confirm environment'
        self.assertIn('未明确',event_reason(c))
        c = self.candidate();c['scopes']=['ui']
        self.assertIn('人工',event_reason(c))
        c = self.candidate();c['source_messages'][0]['action']='WITHDRAWN'
        self.assertIn('撤回',event_reason(c))

    def test_ready_event_uses_pipeline_once_without_jira_writes(self):
        check = {'status':'READY','reasons':[],'execution':{'plan_sha256':'x'},'sources_sha256':'s','policy_sha256':'p'}
        jira = Mock();jira.resolve_story.return_value={'story':self.story}
        runner = Mock(return_value={'status':'FAIL'})
        preview = {'candidates':[self.candidate()]}
        with patch('qa_workflow.service.preflight',side_effect=lambda *a,**kw:copy.deepcopy(check)):
            result = process_candidates(self.state,self.config,preview,execute=True,jira=jira,pipeline=runner)
            self.assertEqual(result[0]['status'],'FAIL')
            result = process_candidates(self.state,self.config,preview,execute=True,jira=jira,pipeline=runner)
            self.assertEqual(result[0]['status'],'ALREADY_CLAIMED')
            runner.assert_called_once()
            self.assertEqual({c[0] for c in jira.mock_calls},{'resolve_story'})

    def draft(self):
        return {'summary':'边界测试','questions':[],'cases':[{'id':'DRAFT-001','layer':'API','title':'独立公式','preconditions':'非零源数据',
            'steps':['独立计算并比较'],'expected':'匹配已确认公式','source_ids':['design.md'],'acceptance_ids':['AC-02'],'data_requirements':['独立金额样本'],'blockers':['样本待准备']}]}

    def test_generated_cases_keep_sources_and_do_not_replace_plan(self):
        path = self.root/'requirements'/self.story/'plan.json';before = path.read_bytes()
        model = Mock(return_value=self.draft())
        value = generate(self.state,self.story,{},model)
        self.assertEqual(value['status'],'DRAFT')
        self.assertEqual(path.read_bytes(),before)
        csv = next(self.state.directory.glob('generation/*/*/cases.csv')).read_bytes()
        self.assertTrue(csv.startswith(b'\xef\xbb\xbf'))
        self.assertFalse(csv.startswith(b'\xef\xbb\xbf\xef\xbb\xbf'))
        generate(self.state,self.story,{},model)
        model.assert_called_once()
        blocked = self.draft();blocked['cases'][0]['acceptance_ids']=[]
        self.assertEqual(validate(blocked,context(self.root,self.story)),blocked)
        blocked['cases'][0]['blockers']=[]
        with self.assertRaises(ValueError): validate(blocked,context(self.root,self.story))
        bad = self.draft();bad['cases'][0]['source_ids']=['invented.md']
        with self.assertRaises(ValueError): validate(bad,context(self.root,self.story))
        bad = self.draft();bad['cases'][0]['acceptance_ids']=['AC-999']
        with self.assertRaises(ValueError): validate(bad,context(self.root,self.story))

    def test_html_escapes_manual_content_and_bug_candidates(self):
        text = render(self.root,{'requirements':[],'bad':'</script><script>alert(1)</script>'})
        self.assertNotIn('</script><script>alert(1)',text)
        folder = self.root/'review';folder.mkdir()
        render_report(folder,{'story':self.story,'environment':'FAT','build':'v1'},
                      {'status':'FAIL','summary':'<script>bad</script>','results':[],'bugs':[]})
        html = (folder/'report.html').read_text()
        self.assertIn('&lt;script&gt;',html)
        self.assertIn('确认后才建单',html)


    def test_document_sync_tracks_commits_deletions_and_does_not_checkout(self):
        from qa_workflow.documents import sync
        for name in ('scan-bruno-interfaces.py','build-api-catalog.py'):
            (self.root/'scripts'/name).write_bytes((ROOT/'scripts'/name).read_bytes())
        (self.root/'api/catalog').mkdir(parents=True)
        repo = self.root/'source';repo.mkdir()
        def git(*args):
            return subprocess.run(['git','-C',str(repo),*args],check=True,capture_output=True).stdout.decode().strip()
        git('init');git('config','user.email','fixture@example.invalid');git('config','user.name','Fixture')
        source = repo/'collection';source.mkdir()
        path = source/'first.bru'
        path.write_text('meta {\n name: ISOP-2028 example\n}\nget {\n url: {{api_url}}/example\n}\n')
        git('add','.');git('commit','-m','initial')
        first = git('rev-parse','HEAD')
        a = sync(self.state,source)
        self.assertTrue(a['baseline'])
        self.assertEqual(a['changes'][0]['requirements'][0]['story'],self.story)
        path.unlink()
        (source/'second.bru').write_text('meta {\n name: ISOP-2028 changed\n}\nget {\n url: {{api_url}}/new\n}\n')
        git('add','.');git('commit','-m','changed')
        head = git('rev-parse','HEAD')
        (source/'uncommitted.bru').write_text('local user change')
        b = sync(self.state,source)
        self.assertEqual(b['previous_commit'],first)
        self.assertEqual({c['change'] for c in b['changes']},{'deleted','modified_or_added'})
        self.assertEqual(git('rev-parse','HEAD'),head)
        self.assertTrue((source/'uncommitted.bru').exists())
        self.assertTrue(sync(self.state,source)['unchanged'])

    def test_result_import_excludes_manual_and_partial_checkpoints(self):
        from qa_core.execution_plan import expand
        plan = json.loads((self.root/'requirements'/self.story/'plan.json').read_text())
        case = next(c for c in expand(plan) if c.get('steps') and c['review']['类型']=='API')
        folder = self.root/'reports/qa'/self.story/'run';folder.mkdir(parents=True)
        (folder/'cases.snapshot.json').write_text(json.dumps([case['review']]))
        (folder/'plan.snapshot.json').write_text(json.dumps(plan))
        result = {'mode':'execution','requirement':self.story,'run_id':'run','source_time':'2026-09-14T01:00:00Z',
                  'cases_sha256':'pinned','results':[{'id':case['id'],'status':'FAIL'}]}
        path = folder/'result.json';path.write_text(json.dumps(result))
        collect_results(self.state)
        row = next(r for r in self.state.view()['requirements'] if r['story']==self.story)
        self.assertEqual(row['automatic'],[])
        result['timings_ms']={'report':5};path.write_text(json.dumps(result))
        collect_results(self.state);collect_results(self.state)
        row = next(r for r in self.state.view()['requirements'] if r['story']==self.story)
        self.assertEqual(len(row['automatic']),1)
        self.assertEqual(row['automatic'][0]['status'],'FAIL')
        result['mode']='evidence-summary';path.write_text(json.dumps(result))
        collect_results(self.state)
        row = next(r for r in self.state.view()['requirements'] if r['story']==self.story)
        self.assertEqual(len(row['automatic']),1)

    def test_browser_manual_edit_reload_keeps_api_failure(self):
        self.state.append(self.story,'automatic',{'status':'FAIL','time':'2026-09-14','case_ids':['case-1'],'report':'reports/qa/test/results.html'})
        server = HTTPServer(('127.0.0.1',0),handler(self.root,self.state.directory,'browser-token'))
        thread = threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            env = {**os.environ,'QA_STATUS_URL':f'http://127.0.0.1:{server.server_port}'}
            result = subprocess.run(['node',str(ROOT/'tests/unit/status-editor.mjs')],cwd=ROOT,env=env,capture_output=True,text=True,timeout=45)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        finally:
            server.shutdown();server.server_close();thread.join()

    def test_web_origin_private_files_and_persistence(self):
        server = HTTPServer(('127.0.0.1',0),handler(self.root,self.state.directory,'test-token'))
        thread = threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        origin = f'http://127.0.0.1:{server.server_port}'
        try:
            response = json.load(urllib.request.urlopen(origin+'/api/status'))
            self.assertEqual(response['token'],'test-token')
            body = json.dumps({'story':self.story,**self.edit()}).encode()
            request = urllib.request.Request(origin+'/api/manual',data=body,headers={'Content-Type':'application/json','X-QA-Token':'test-token','Origin':origin})
            self.assertTrue(json.load(urllib.request.urlopen(request))['saved'])
            bad = urllib.request.Request(origin+'/api/manual',data=body,headers={'X-QA-Token':'test-token','Origin':'https://evil.example'})
            with self.assertRaises(urllib.error.HTTPError) as error: urllib.request.urlopen(bad)
            self.assertEqual(error.exception.code,403)
            for path in ('/.env.fat','/evidence/reports/qa/x/private-checkpoints.json','/evidence/../../.env.fat'):
                with self.assertRaises(urllib.error.HTTPError): urllib.request.urlopen(origin+path)
            row = next(r for r in self.state.view()['requirements'] if r['story']==self.story)
            self.assertEqual(row['manual']['ui']['author'],'测试人')
        finally:
            server.shutdown();server.server_close();thread.join()
