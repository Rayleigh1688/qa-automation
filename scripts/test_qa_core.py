"""Wire fixtures and legacy entry compatibility for the infrastructure migration."""
import importlib.util
import unittest
from pathlib import Path

import api_contracts
from qa_core import codec, contracts


class CodecWireTests(unittest.TestCase):
    def test_known_wire_encodings(self):
        fixtures = [
            (None, 'f6'), (False, 'f4'), (True, 'f5'),
            (0, '00'), (23, '17'), (24, '1818'), (256, '190100'),
            (65536, '1a00010000'), (4294967296, '1b0000000100000000'),
            (-1, '20'), (-25, '3818'), ('a', '6161'),
            ([1, True], '8201f5'), ({'status': True}, 'a166737461747573f5'),
        ]
        for value, encoded in fixtures:
            with self.subTest(value=value):
                self.assertEqual(codec.cbor_encode(value).hex(), encoded)
                self.assertEqual(codec.cbor_decode(bytes.fromhex(encoded)), value)

    def test_nested_unicode_response(self):
        payload = {'status': True, 'data': {'name': '测试', 'rows': [0, -1, None]}}
        decoded, sample = codec.decode_body_sample(codec.cbor_encode(payload))
        self.assertEqual(decoded, payload)
        self.assertIn('测试', sample)

    def test_float_response(self):
        self.assertEqual(codec.cbor_decode(bytes.fromhex('fa3fc00000')), 1.5)
        self.assertEqual(codec.cbor_decode(bytes.fromhex('fb3ff8000000000000')), 1.5)

    def test_json_fallback_and_empty_response(self):
        self.assertEqual(codec.decode_body_sample(b'{"status":true}')[0], {'status': True})
        self.assertEqual(codec.decode_body_sample(b'  [true, null]')[0], [True, None])
        self.assertEqual(codec.decode_body_sample(b''), (None, ''))

    def test_unsupported_encoding_and_empty_cbor_remain_errors(self):
        with self.assertRaises(TypeError):
            codec.cbor_encode(1.5)
        with self.assertRaises(codec.CborDecodeError):
            codec.cbor_decode(b'')


class LegacyImportsTests(unittest.TestCase):
    def test_smoke_runner_reexports_codec_for_existing_consumers(self):
        path = Path(__file__).with_name('api-smoke-runner.py')
        spec = importlib.util.spec_from_file_location('legacy_smoke_codec_test', path)
        smoke = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(smoke)
        for name in ('cbor_encode', 'cbor_decode', 'decode_body_sample', 'CborDecodeError'):
            self.assertIs(getattr(smoke, name), getattr(codec, name))

    def test_old_contract_imports_use_same_implementation(self):
        self.assertIs(api_contracts.resolve_dynamic_values, contracts.resolve_dynamic_values)
        self.assertIs(api_contracts.normalize_request_template, contracts.normalize_request_template)
        self.assertIs(api_contracts.TIME_TOKENS, contracts.TIME_TOKENS)


if __name__ == '__main__':
    unittest.main()
