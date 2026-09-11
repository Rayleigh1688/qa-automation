import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import unittest
from support import ROOT
from filbet.requirement_session import Session
from filbet.requirement_kyc import png_bytes, legacy_environment
from qa_core.codec import cbor_decode
import os


class SessionTests(unittest.TestCase):
    def test_explicit_tokens_encodings_and_redirect_no_replay(self):
        requests = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                payload = self.rfile.read(int(self.headers.get('Content-Length',0)))
                requests.append((self.path,self.headers.get('t'),self.headers.get('Content-Type'),payload))
                if self.path == '/redirect':
                    self.send_response(307);self.send_header('Location','/replayed');self.end_headers();return
                self.send_response(200);self.end_headers();self.wfile.write(b'{"status":false,"data":null}')
        server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread = threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            base = 'http://127.0.0.1:'+str(server.server_port)
            a,b = Session(base,{}),Session(base,{})
            a.token,b.token = 'actor-A','actor-B'
            self.assertFalse(a.request('POST','/cbor',body={'id':9223372036854775807})['body']['status'])
            b.request('POST','/json',body={'id':None},encoding='json')
            a.request('POST','/upload',encoding='multipart',upload=(png_bytes(512001),'qa.png','image/png'),auth='missing')
            self.assertEqual(a.request('POST','/redirect',body={'id':1})['http'],307)
            self.assertEqual([r[1] for r in requests],['actor-A','actor-B',None,'actor-A'])
            self.assertEqual(cbor_decode(requests[0][3]),{'id':9223372036854775807})
            self.assertEqual(json.loads(requests[1][3]),{'id':None})
            self.assertIn(png_bytes(512001),requests[2][3])
            self.assertEqual(len(requests),4)
        finally:
            server.shutdown();server.server_close();thread.join()

    def test_legacy_setup_environment_restored_on_failure(self):
        old = dict(os.environ)
        with self.assertRaises(RuntimeError):
            with legacy_environment({'ADMIN_TOKEN':'temporary'}):
                self.assertEqual(dict(os.environ),{'ADMIN_TOKEN':'temporary'})
                raise RuntimeError()
        self.assertEqual(dict(os.environ),old)

    def test_valid_png_exact_sizes(self):
        for size in [499999,500000,511999,512000,512001]:
            data = png_bytes(size)
            self.assertEqual(len(data),size)
            self.assertTrue(data.startswith(b'\x89PNG\r\n\x1a\n'))

    def test_allocator_null_only_with_explicit_zero_total(self):
        from filbet.controlled import ControlledFlow
        from types import SimpleNamespace
        from unittest.mock import patch
        flow = ControlledFlow()
        args = SimpleNamespace(timeout=1,insecure=False,body_format='cbor')
        for total,allowed in [(0,True),(1,False),(None,False),(False,False)]:
            result={'status':200,'decoded_body':{'status':True,'data':{'d':None,'t':total}}}
            with patch.object(flow.smoke,'request_once',return_value=result):
                if allowed: self.assertFalse(flow.admin_member_exists(args,'9000000001'))
                else:
                    with self.assertRaises(SystemExit): flow.admin_member_exists(args,'9000000001')

    def test_snapshot_preserves_string_ids(self):
        from filbet.requirement_kyc import normalized
        self.assertEqual(normalized({'id':'9223372036854775807','attachments':'{"face":"123.webp"}'}),{'id':'9223372036854775807','attachments':{'face':'123.webp'}})
