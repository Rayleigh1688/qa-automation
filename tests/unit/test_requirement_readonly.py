import unittest
from unittest.mock import patch
from types import SimpleNamespace
import support
from filbet.requirement_readonly import validate, session_for
from filbet.requirement_session import Session

class ReadOnlyQueries(unittest.TestCase):
    def test_unknown_or_write_route_rejected(self):
        for route in ['notify-read','/admin/promo/update','pagcor-export']:
            with self.assertRaises(ValueError):validate({}, {'params':{'route':route}})

    def test_client_login_does_not_accept_business_failure(self):
        s=Session('https://example.test',{'CLIENT_PHONE':'test','CLIENT_PASSWORD':'test'},admin=False)
        with patch.object(s,'request',return_value={'http':200,'body':{'status':False,'data':'not-a-token'}}):
            with self.assertRaises(RuntimeError):s.login_client_password()
        self.assertEqual(s.token,'')

    def test_failed_login_cached_to_prevent_repeated_attempts(self):
        a=SimpleNamespace(config={'API_URL':'https://example.test'},sessions={},args=SimpleNamespace(timeout=1,insecure=False),login_ms=0)
        with patch('filbet.requirement_readonly.Session.login_client_password',side_effect=RuntimeError) as login:
            for _ in range(2):
                with self.assertRaises(RuntimeError):session_for(a,'client')
            self.assertEqual(login.call_count,1)
