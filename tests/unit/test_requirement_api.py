import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from filbet import requirement_api as api


class RequirementApiTests(unittest.TestCase):
    def test_empty_rows_do_not_prove_filter(self):
        case = {'expect': 'success', 'requires_rows': True, 'checks': [
            {'op': 'rows_eq', 'path': 'data.d', 'field': 'jp_type', 'value': 99}]}
        result = {'status': 200, 'decoded_body': {'status': True, 'data': {'d': []}}}
        self.assertEqual(api.evaluate(case, result)[0], 'BLOCKED')
        result['decoded_body']['data']['d'] = [{'jp_type': 1}]
        self.assertEqual(api.evaluate(case, result)[0], 'FAIL')

    def test_auth_failure_is_not_any_error(self):
        case = {'expect': 'auth_rejected'}
        for status in ('ERROR', 404, 500):
            self.assertEqual(api.evaluate(case, {'status': status, 'decoded_body': {'status': False}})[0], 'FAIL')
        result = {'status': 401, 'decoded_body': {'status': False, 'data': {'uid': 'private'}}}
        self.assertEqual(api.evaluate(case, result)[0], 'FAIL')
        result['decoded_body']['data'] = None
        self.assertEqual(api.evaluate(case, result)[0], 'PASS')
        result['status'] = 200
        result['decoded_body']['data'] = 'token'
        self.assertEqual(api.evaluate(case, result)[0], 'PASS')
        result['decoded_body']['data'] = 'some-private-token'
        self.assertEqual(api.evaluate(case, result)[0], 'FAIL')

    def test_validation_must_match_parameter_error(self):
        case = {'expect': 'validation_rejected', 'error_pattern': 'time'}
        result = {'status': 200, 'decoded_body': {'status': False, 'message': 'token expired'}}
        self.assertEqual(api.evaluate(case, result)[0], 'FAIL')
        result['decoded_body']['message'] = 'missing start_time'
        self.assertEqual(api.evaluate(case, result)[0], 'PASS')

    def test_amounts_use_decimal_and_reject_nan(self):
        case = {'expect': 'success', 'checks': [{'op': 'jp_multi', 'path': 'data.d'}]}
        row = {'jp_type': 99, 'jp_winning': '0.3', 'jackpot_details': [
            {'jp_type': 1, 'jp_winning': '0.1'}, {'jp_type': 4, 'jp_winning': '0.2'}]}
        result = {'status': 200, 'decoded_body': {'status': True, 'data': {'d': [row]}}}
        self.assertEqual(api.evaluate(case, result)[0], 'PASS')
        row['jp_winning'] = 'NaN'
        self.assertEqual(api.evaluate(case, result)[0], 'FAIL')

    def test_observation_does_not_persist_private_response(self):
        result = {'status': 200, 'url': 'private-url', 'decoded_body': {'status': False,
            'msg': 'private-phone', 'token': 'private-token', 'data': {'d': [{'uid': 'private-id'}]}}}
        self.assertNotIn('private', json.dumps(api.observation(result)))

    def test_cases_reference_acceptance_and_reject_unknown_assertions(self):
        for key in ('ISOP-2027', 'ISOP-2032', 'ISOP-2037', 'ISOP-2043'):
            api.load_suite(key)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'requirements/ISOP-1'
            (folder / 'api').mkdir(parents=True)
            (folder / 'test-cases.md').write_text('| ISOP-1-C01 |')
            case = {'id': 'test', 'case_ids': ['ISOP-1-C01'], 'expect': 'success',
                    'request': {'method': 'POST', 'path': '/admin/record/bet'}, 'checks': [{'op': 'typo'}]}
            (folder / 'api/cases.json').write_text(json.dumps({'requirement': 'ISOP-1', 'cases': [case]}))
            with patch.object(api, 'ROOT', Path(tmp)), self.assertRaises(ValueError):
                api.load_suite('ISOP-1')

    def test_invalid_auth_is_restored_after_network_exception(self):
        case = {'id': 'auth', 'auth': 'invalid', 'request': {'method': 'GET', 'path': '/admin/kyc/review/list'}}
        with patch.dict(api.os.environ, {'ADMIN_TOKEN': 'original'}), patch.object(api.smoke, 'request_once', side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                api.execute_case(case, SimpleNamespace(timeout=1, insecure=False, body_format='cbor'))
            self.assertEqual(api.os.environ['ADMIN_TOKEN'], 'original')


if __name__ == '__main__':
    unittest.main()
