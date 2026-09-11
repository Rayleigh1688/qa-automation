"""Local HTTPS fixture proves the real Playwright scan/plan/run protocol."""
import http.server
import json
import shutil
import ssl
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from support import ROOT


class TelegramUIBrowserTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node') and shutil.which('openssl'), 'node and openssl required')
    def test_browser_discovery_and_policy_block_are_not_false_passes(self):
        with tempfile.TemporaryDirectory(prefix='telegram-ui-') as directory:
            folder = Path(directory)
            key, cert = folder / 'key.pem', folder / 'cert.pem'
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                            '-subj', '/CN=localhost', '-keyout', str(key), '-out', str(cert)],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            class Handler(http.server.BaseHTTPRequestHandler):
                def log_message(self, *args): pass
                def do_GET(self):
                    self.send_response(200); self.send_header('Content-Type', 'text/html'); self.end_headers()
                    if self.path == '/business-failure':
                        self.wfile.write(b'{"status":false,"data":"rejected"}')
                        return
                    self.wfile.write(b'''<div data-testid="ready">Ready</div><button onclick="fetch('/query')"><span role="img" aria-label="search"></span>Query</button>
                        <div role="tab" id="rc-tabs-37-tab-reviewed" onclick="fetch('/business-failure')">Reviewed</div>
                        <button id="write" onclick="fetch('/write',{method:'POST'})">Write</button>''')
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain(cert, key)
            server.socket = ctx.wrap_socket(server.socket, server_side=True)
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                origin = f'https://127.0.0.1:{server.server_port}'
                config = {'env_file': str(folder / 'empty.env'), 'ignore_https_errors': True,
                          'auth': {'ready': {'testId': 'ready'}},
                          'pages': {'list': {'url': origin + '/', 'ready': {'testId': 'ready'}}},
                          'action_timeout_ms': 1000,
                          'requests': [{'id': 'business', 'origin': origin, 'method': 'GET', 'path_pattern': '^/business-failure$', 'business_success': True},
                                       {'id': 'read', 'origin': origin, 'method': 'GET', 'path_pattern': '^/.*$'}]}
                (folder / 'ui-config.json').write_text(json.dumps(config))
                def run(mode):
                    return subprocess.run(['node', 'scripts/telegram-ui.mjs', str(folder), mode],
                                          cwd=ROOT, capture_output=True, text=True, timeout=45)
                result = run('scan')
                if 'Executable doesn\'t exist' in result.stderr:
                    self.skipTest('Playwright browser not installed')
                self.assertEqual(result.returncode, 0, result.stderr)
                scan = json.loads((folder / 'scan.json').read_text())
                elements = scan['pages']['list']['elements']
                targets = {e['name']: e['id'] for e in elements if e['name']}
                plan = {'cases': [
                    {'id': 'U1', 'case_id': 'C1', 'page': 'list', 'basis': 'fixture', 'blocked': '', 'steps': [
                        {'op': 'click', 'target': targets['Query'], 'value': ''},
                        {'op': 'assert_response', 'target': 'read', 'value': '200'}]},
                    {'id': 'U2', 'case_id': 'C2', 'page': 'list', 'basis': 'fixture', 'blocked': '', 'steps': [
                        {'op': 'click', 'target': targets['Write'], 'value': ''},
                        {'op': 'assert_visible', 'target': targets['Write'], 'value': ''}]},
                    {'id': 'U3', 'case_id': 'C3', 'page': 'list', 'basis': 'HTTP 200 with business rejection must fail', 'blocked': '', 'steps': [
                        {'op': 'click', 'target': targets['Reviewed'], 'value': ''},
                        {'op': 'assert_response', 'target': 'business', 'value': '200'}]},
                    {'id': 'U4', 'case_id': 'C4', 'page': 'list', 'basis': 'unknown selector is an execution error', 'blocked': '', 'steps': [
                        {'op': 'click', 'target': 'missing-target', 'value': ''}]}]}
                (folder / 'ui-plan.json').write_text(json.dumps(plan))
                result = run('run')
                self.assertEqual(result.returncode, 1, result.stderr)
                rows = json.loads((folder / 'ui-result.json').read_text())['results']
                self.assertEqual([r['status'] for r in rows], ['PASS', 'BLOCKED', 'FAIL', 'ERROR'])
                self.assertEqual(rows[3]['assertions'], [])
                self.assertGreater(rows[1]['blocked_requests'], 0)
                self.assertFalse(next(r for r in rows[2]['network'] if r['rule'] == 'business')['business_success'])
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=2)
