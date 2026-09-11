"""Real local browser checks for request correlation, ambiguity, obstruction and isolation."""
import copy
import base64
import http.server
import json
import os
import signal
import sys
from pathlib import Path
import tempfile
import threading
import unittest
from support import ROOT
from qa_core.json_worker import JsonWorker
from qa_core.execution_plan import validate
from filbet.requirement_adapter import METHODS


class UIContractTests(unittest.TestCase):
    def test_bad_ui_assets_actions_responses_fail_offline(self):
        plan=json.loads((ROOT/'requirements/ISOP-2027/plan.json').read_text())
        plan['cases']=[next(c for c in plan['cases'] if c['id']=='2027-UI-001')]
        validate(plan,METHODS)
        for change in [{'element':'missing'},{'op':'eval'}, {'expect':[]}, {'response':{'contract':'missing'}}]:
            bad=copy.deepcopy(plan); bad['cases'][0]['steps'][3].update(change)
            with self.assertRaises(ValueError): validate(bad,METHODS)


class RequirementUIBrowserTests(unittest.TestCase):
    def test_real_actions_never_mask_stale_response_duplicate_or_overlay(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                self.rfile.read(int(self.headers.get('Content-Length',0)))
                self.send_response(200);self.end_headers();self.wfile.write(b'{"status":true}')
            def do_GET(self):
                self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers()
                if self.path.startswith('/api'):
                    self.wfile.write(b'{"status":false}');return
                self.wfile.write(b'''<div id="ready">ready</div>
                <script>fetch('/api?uid=old');</script>
                <button id="query" onclick="fetch('/api?uid=current')">Query</button>
                <button id="stale">No request</button>
                <button class="duplicate">Duplicate</button><button class="duplicate">Duplicate</button>
                <input id="value"><input id="file" type="file" onchange="let f=new FormData();f.append('file',this.files[0]);fetch('/upload',{method:'POST',body:f})">
                <button id="blocked" style="position:absolute;left:0;top:200px">Restore</button>
                <div style="position:absolute;left:0;top:200px;width:200px;height:60px;z-index:5">cover</div>
                <button id="write" onclick="fetch('/write',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({uid:'foreign'})})">Write</button>''')
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        with tempfile.TemporaryDirectory() as directory:
            worker=JsonWorker(['node','scripts/requirement-ui-worker.mjs'],cwd=ROOT)
            origin=f'http://127.0.0.1:{server.server_port}'
            assets={'auth':{'path':'/','steps':[],'ready':{'css':'#ready'}},'requests':[{'service':'admin','method':'GET','path_pattern':'^/.*$'}]}
            contracts={'upload':{'service':'admin','path':'/upload','method':'POST','write':True,'scope':'test'},'query':{'service':'admin','path':'/api','method':'GET','write':False},'write':{'service':'admin','path':'/write','method':'POST','write':True,'ownership':'uid','scope':'test'}}
            try:
                self.assertTrue(worker.call({'op':'init','config':{'origin':origin,'assets':assets,'contracts':contracts,'scopes':['test'],'folder':directory,'insecure':False,'timeout_ms':400}})['ready'])
                def run(step,actor='A'):
                    return worker.call({'actor':actor,'caseId':'local','auth':{},'owned':{'uid':['current']},'step':{'id':'action',**step},'png':base64.b64encode(b'local synthetic bytes').decode()})
                live=run({'op':'click','target':{'css':'#query'},'response':{'contract':'query','match':{'uid':'current'}}})
                self.assertEqual(live['request_count'],1);self.assertFalse(live['body']['status'])
                negative=run({'op':'click','target':{'css':'#stale'},'response':{'contract':'query','none':True,'window_ms':100,'match':{'uid':'old'}}})
                self.assertEqual(negative['request_count'],0)
                uploaded=run({'op':'upload','target':{'css':'#file'},'response':{'contract':'upload','match':{}}})
                self.assertEqual(uploaded['request_count'],1);self.assertTrue(uploaded['body']['status'])
                stale=run({'op':'click','target':{'css':'#stale'},'response':{'contract':'query','match':{'uid':'old'}}})
                self.assertTrue(stale['execution_error'])
                duplicate=run({'op':'click','target':{'css':'.duplicate'}})
                self.assertTrue(duplicate['execution_error'])
                blocked=run({'op':'click','target':{'css':'#blocked'}})
                self.assertFalse(blocked['execution_error']);self.assertFalse(blocked['checks']['completed'])
                self.assertEqual(blocked['error_category'],'pointer-intercepted')
                self.assertTrue((Path(directory)/blocked['evidence']).exists())
                run({'op':'fill','target':{'css':'#value'},'value':'actor-a'})
                isolated=run({'op':'observe','target':{'css':'#value'},'property':'value'},actor='B')
                self.assertEqual(isolated['value'],'')
                denied=run({'op':'click','target':{'css':'#write'},'response':{'contract':'write','match':{'uid':'foreign'}}})
                self.assertTrue(denied['execution_error']);self.assertFalse(denied['checks']['policy'])
                intents=[json.loads(line) for line in (Path(directory)/'private-ui-intents.jsonl').read_text().splitlines()]
                self.assertEqual([x['path'] for x in intents],['/upload'])
            finally:
                worker.close();server.shutdown();server.server_close();thread.join(timeout=2)


class JsonWorkerLifecycleTests(unittest.TestCase):
    def test_timeout_reaps_worker_and_double_close_is_safe(self):
        previous=signal.getsignal(signal.SIGTERM)
        worker=JsonWorker([sys.executable,'-c','import sys,time;sys.stdin.readline();time.sleep(30)'],cwd=ROOT)
        with self.assertRaises(RuntimeError): worker.call({'op':'never-respond'},timeout=0.05)
        self.assertIsNotNone(worker.child.poll())
        worker.close()
        self.assertEqual(signal.getsignal(signal.SIGTERM),previous)
        with self.assertRaises(RuntimeError): worker.call({'op':'closed'})
