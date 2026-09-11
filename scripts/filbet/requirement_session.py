"""Explicit per-actor HTTP sessions; no global token mutation or request retries."""
import json
import ssl
import time
import uuid
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler
from qa_core.codec import cbor_encode, decode_body_sample
from totp import current_totp


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Session:
    def __init__(self, base, config, *, admin=True, timeout=15, insecure=False):
        parsed = urlsplit(base)
        if parsed.scheme not in {'http', 'https'} or not parsed.netloc or parsed.query or parsed.fragment or parsed.username:
            raise ValueError('invalid service URL')
        self.base, self.config, self.admin = base.rstrip('/'), dict(config), admin
        self.timeout, self.token = timeout, ''
        self.headers = {'accept':'application/json', 'd':config.get('DEVICE','25'),
                        'lang':config.get('ADMIN_LANG_HEADER' if admin else 'LANG_HEADER','en' if admin else 'en_US')}
        if admin:
            self.headers.update({'client-id':config.get('ADMIN_CLIENT_ID','123'),
                'client-version':config.get('ADMIN_CLIENT_VERSION','Chrome/151.0.0.0'),
                'x-device-id':str(uuid.uuid4())})
        context = ssl._create_unverified_context() if insecure else ssl.create_default_context()
        self.opener = build_opener(NoRedirect(), HTTPSHandler(context=context))

    def request(self, method, path, *, body=None, query=None, headers=None, encoding='cbor', auth='valid', upload=None):
        if not path.startswith('/') or path.startswith('//') or '?' in path or '..' in path:
            raise ValueError('request must use a contract path')
        url = self.base + path + ('?' + urlencode(query, doseq=True) if query else '')
        hdr = {**self.headers, **(headers or {})}
        if any(k.lower() in {'t','authorization','cookie','host'} for k in (headers or {})):
            raise ValueError('authentication headers belong to session')
        if auth == 'valid' and self.token: hdr['t'] = self.token
        if auth == 'invalid': hdr['t'] = 'invalid-requirement-test-token'
        payload = None
        if encoding == 'multipart':
            boundary = 'qa-' + uuid.uuid4().hex
            data, filename, mime = upload
            if any(x in filename + mime for x in ['\r','\n','"']): raise ValueError('invalid upload metadata')
            payload = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: {mime}\r\n\r\n').encode() + data + f'\r\n--{boundary}--\r\n'.encode()
            hdr['content-type'] = 'multipart/form-data; boundary=' + boundary
        elif body is not None:
            payload = cbor_encode(body) if encoding == 'cbor' else json.dumps(body).encode()
            hdr.setdefault('content-type', 'application/cbor' if encoding == 'cbor' else 'application/json')
        started = time.monotonic()
        request = Request(url, data=payload, headers=hdr, method=method)
        try:
            response = self.opener.open(request, timeout=self.timeout)
        except HTTPError as error:
            response = error
        with response:
            decoded, _ = decode_body_sample(response.read())
            return {'http':response.code, 'body':decoded, 'elapsed_ms':round((time.monotonic()-started)*1000)}

    def login(self):
        conf = self.config
        code = conf.get('ADMIN_GOOGLE_CODE')
        if not code:
            secret = conf.get('ADMIN_LOGIN_TOTP_SECRET') or conf.get('ADMIN_APPROVAL_TOTP_SECRET')
            if not secret: raise ValueError('admin login code missing')
            code = current_totp(secret, algorithm=conf.get('ADMIN_LOGIN_TOTP_ALGORITHM') or conf.get('ADMIN_APPROVAL_TOTP_ALGORITHM','SHA1'))
        body = {'email':conf['ADMIN_EMAIL'], 'password':conf['ADMIN_PASSWORD']}
        first = self.request('POST','/admin/login/auth',body=body)
        if first['http'] != 200 or first['body'].get('status') is not True:
            raise RuntimeError('admin login auth rejected')
        result = self.request('POST','/admin/login',body={**body,'google_code':int(code),'google_secret':conf.get('ADMIN_GOOGLE_SECRET','')})
        if result['http'] != 200 or not isinstance(result['body'], dict) or result['body'].get('status') is not True or not isinstance(result['body'].get('data'),str) or not result['body']['data']:
            raise RuntimeError('admin login rejected')
        self.token = conf.get('ADMIN_TOKEN_PREFIX','') + result['body']['data']

    def login_client_password(self):
        """FAT read-only client lane; issue a fresh token without global state."""
        if self.admin or self.config.get('CLIENT_AUTH_MODE', 'password') != 'password':
            raise ValueError('client password lane required')
        result = self.request('POST', '/member/v2/login', body={
            'login_text': self.config['CLIENT_PHONE'], 'password': self.config['CLIENT_PASSWORD']}, auth='missing')
        from filbet.smoke import extract_token
        token = extract_token({'decoded_body': result.get('body')})
        if result['http'] != 200 or not token:
            raise RuntimeError('client login rejected')
        self.token = token
