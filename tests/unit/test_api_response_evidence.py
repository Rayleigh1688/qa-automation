import io
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from support import ROOT
from filbet.requirement_session import Session
from qa_core.api_response_evidence import MAX_ITEMS
from qa_core.plan_runner import execute


class ApiResponseEvidenceTests(unittest.TestCase):
    def run_response(self, body, *, fields=None):
        checks = [{'path': 'http', 'op': 'eq', 'value': 200},
                  {'path': 'body.status', 'op': 'eq', 'value': True}]
        if fields:
            checks.append({'path': 'body', 'op': 'fields_absent_or', 'value': fields})
        step = {
            'id': 'fixture', 'action': 'api', 'actor': 'guest', 'contract': 'fixture',
            'headers': {'x-device-id': 'fixture-device'},
            'query': {'page': '${page}', 'member_id': '${member}'}, 'expect': checks,
        }
        case = {'id': 'EXAMPLE', 'steps': [step], 'variables': {'page': 2, 'member': 14692835}}
        adapter = SimpleNamespace(
            plan={'contracts': {'fixture': {'method': 'GET', 'path': '/fixture', 'encoding': 'cbor'}}},
            execute=lambda step, case_id: {
                'http': 200, 'body': body, 'decode_status': 'decoded', 'body_bytes': 120,
            },
        )
        return execute([case], adapter, 'offline')[0]['steps'][0]

    def test_reviewed_message_and_full_field_counts_survive_bounded_preview(self):
        rows = [{'updated_uid': 0, 'maintainer': ''} for _ in range(MAX_ITEMS + 1)]
        rows.append({'updated_uid': 998715346, 'maintainer': 'private-person-value'})
        body = {'status': True, 'message': 'Success', 'data': {'d': rows, 's': 14, 't': 25}}
        step = self.run_response(body, fields={'updated_uid': [None, '', 0],
                                               'maintainer': ['', None], 'oauth_secrets': []})
        self.assertEqual(step['status'], 'FAIL')
        self.assertEqual(step['request']['query'], {'page': 2, 'member_id': '<redacted>'})
        self.assertEqual(step['request']['path'], '/fixture')
        self.assertEqual(step['response']['body']['message'], 'Success')
        self.assertEqual(step['response']['body']['data']['d'][0]['updated_uid'], 0)
        self.assertTrue(step['response']['truncated'])
        self.assertEqual(step['response']['body_bytes'], 120)
        check = step['assertions'][-1]
        self.assertEqual(check['expected']['updated_uid'], [None, '', 0])
        self.assertEqual(check['field_observations']['updated_uid'],
                         {'integer_zero': MAX_ITEMS + 1, 'integer_nonzero': 1})
        self.assertEqual(check['field_observations']['oauth_secrets'], {})
        self.assertEqual(check['unexpected_fields'], ['maintainer', 'updated_uid'])
        for private in ('fixture-device', '998715346', '14692835', 'private-person-value'):
            self.assertNotIn(private, json.dumps(step))

    def test_unreviewed_text_keys_and_malformed_status_do_not_leak(self):
        body = {
            'status': 'sensitive-status-text', 'message': 'Refused for personal@example.test',
            'data': {'private-account-key': 'private-account-value',
                     'wallet_password': {'status': True, 'secret-fixture': 'private-wallet-value'}},
        }
        step = self.run_response(body, fields={'wallet_password': [None, '']})
        self.assertEqual(step['status'], 'FAIL')
        self.assertEqual(step['response']['body']['message'], '<redacted>')
        self.assertEqual(step['response']['body']['data']['wallet_password'], '<redacted>')
        self.assertEqual(step['assertions'][1]['actual'], '<redacted>')
        self.assertEqual(step['assertions'][1]['actual_type'], 'str')
        for private in ('sensitive-status-text', 'personal@example.test', 'private-account-key',
                        'private-account-value', 'secret-fixture', 'private-wallet-value'):
            self.assertNotIn(private, json.dumps(step))

    def test_preview_prioritizes_asserted_popup_fields_after_wide_unknown_prefix(self):
        unknown = {f'private-field-{index}': 'private-text' for index in range(MAX_ITEMS + 3)}
        rows = [{**unknown, 'trigger_person': '', 'maintainer': ''} for _ in range(MAX_ITEMS + 1)]
        step = self.run_response({'status': True, 'data': rows},
                                 fields={'trigger_person': [], 'maintainer': []})
        response = step['response']
        self.assertEqual(response['body']['data'][0], {'trigger_person': '', 'maintainer': ''})
        self.assertEqual(response['omitted_fields'], len(unknown) * MAX_ITEMS)
        self.assertTrue(response['truncated'])
        self.assertTrue(response['redacted'])
        self.assertNotIn('<hidden key', json.dumps(response))
        self.assertNotIn('private-text', json.dumps(response))
        self.assertEqual(step['status'], 'FAIL')
        self.assertEqual(step['assertions'][-1]['field_observations'],
                         {field: {'empty_string': len(rows)} for field in ('trigger_person', 'maintainer')})

    def test_preview_keeps_asserted_values_inside_masked_dynamic_keys(self):
        body = {'status': True, 'data': {'private-level-name': [{'updated_uid': 0}]}}
        step = self.run_response(body, fields={'updated_uid': [0]})
        self.assertEqual(step['response']['body']['data'], {'<hidden key 1>': [{'updated_uid': 0}]})
        self.assertNotIn('private-level-name', json.dumps(step))

    def test_session_distinguishes_empty_undecodable_and_decoded_null(self):
        for raw, state in ((b'', 'empty'), (b'\x9f', 'undecodable'), (b'\xf6', 'decoded')):
            with self.subTest(state=state):
                stream = io.BytesIO(raw)
                stream.code = 200
                with patch('filbet.requirement_session.build_opener',
                           return_value=SimpleNamespace(open=lambda *args, **kwargs: stream)):
                    observed = Session('https://fixture.invalid', {}).request('GET', '/fixture')
                self.assertEqual(observed['decode_status'], state)
                self.assertEqual(observed['body_bytes'], len(raw))
                self.assertIsNone(observed['body'])
