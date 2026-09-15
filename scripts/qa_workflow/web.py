"""Local HTML state editor; explicit evidence routes never expose private checkpoints/env."""
import json
import secrets
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
from .state import State, collect_results


def render(root, data):
    template = (Path(root)/'scripts/qa_workflow/status-template.html').read_text(encoding='utf-8')
    return template.replace('__INITIAL_DATA__',json.dumps(data,ensure_ascii=False).replace('<','\\u003c'))


def export(state):
    collect_results(state)
    path = state.directory/'status.html'
    path.write_text(render(state.root,state.view()),encoding='utf-8')
    return path


def handler(root, directory, token):
    root = Path(root).resolve()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def send(self, code, body, kind='application/json; charset=utf-8'):
            data = body.encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type',kind)
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('X-Frame-Options','DENY')
            self.end_headers()
            self.wfile.write(data)
        def host_ok(self):
            return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'
        def do_GET(self):
            if not self.host_ok(): return self.send(403,'{}')
            path = unquote(urlsplit(self.path).path)
            if path in ('/','/status.html','/api/status'):
                state = State(root,directory)
                try:
                    collect_results(state)
                    data = state.view()
                    if path == '/api/status': return self.send(200,json.dumps({'data':data,'token':token},ensure_ascii=False))
                    return self.send(200,render(root,data),'text/html; charset=utf-8')
                finally: state.close()
            if path.startswith('/evidence/'):
                relative = Path(path[len('/evidence/'):])
                target = (root/relative).resolve()
                allowed = (target.is_relative_to(root/'requirements') or target.is_relative_to(root/'docs')) and target.suffix=='.md'
                allowed |= target.is_relative_to(root/'reports') and target.name in ('results.html','report.html','report.md','preview.md','changes.json','validated.json')
                if allowed and target.is_file():
                    return self.send(200,target.read_text(encoding='utf-8'),'text/html; charset=utf-8' if target.suffix=='.html' else 'text/plain; charset=utf-8')
            self.send(404,'{}')
        def do_POST(self):
            origin = f'http://127.0.0.1:{self.server.server_port}'
            if not self.host_ok() or self.headers.get('Origin') != origin or not secrets.compare_digest(self.headers.get('X-QA-Token',''),token):
                return self.send(403,json.dumps({'error':'请求来源不匹配'}))
            if self.path != '/api/manual': return self.send(404,'{}')
            state = State(root,directory)
            try:
                length = int(self.headers.get('Content-Length','0'))
                if not 0 < length <= 24000: raise ValueError('请求大小无效')
                value = json.loads(self.rfile.read(length))
                if not isinstance(value,dict): raise ValueError('无效状态记录')
                state.manual(value.get('story'),value)
                export(state)
                self.send(200,'{"saved":true}')
            except (ValueError,KeyError,TypeError) as error:
                self.send(409,json.dumps({'error':str(error)},ensure_ascii=False))
            finally: state.close()
    return Handler


def serve(state, port):
    server = HTTPServer(('127.0.0.1',port),handler(state.root,state.directory,secrets.token_urlsafe(32)))
    print(f'需求状态页面：http://127.0.0.1:{server.server_port}',flush=True)
    try: server.serve_forever()
    finally: server.server_close()
