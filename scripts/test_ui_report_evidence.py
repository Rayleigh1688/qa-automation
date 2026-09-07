import json
import os
import tempfile
import unittest
from pathlib import Path

from ui_report_evidence import build_evidence


class UiEvidenceTests(unittest.TestCase):
    def build(self, root, stats=True):
        source = {'stats': {'startTime': '2026-09-07T03:00:00Z', 'duration': 60000}} if stats else {}
        return build_evidence(source, {}, [], root / 'result.json', root / 'report.html')

    def test_current_game_launch_is_not_reported_as_bet_and_payload_is_not_exported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'client-game-bet-smoke.json').write_text(json.dumps({
                'scannedAt': '2026-09-07T03:00:30Z', 'executeBet': False, 'completedSpinCount': 0,
                'network': [{'kind': 'response', 'ts': 'x', 'url': 'https://host/path?token=secret',
                             'status': 200, 'body': {'password': 'private'}}],
            }))
            result = self.build(root)
            self.assertEqual(result['highlights'][2]['value'], '0 次')
            exported = (root / 'p0-ui-evidence.json').read_text()
            self.assertNotIn('secret', exported)
            self.assertNotIn('private', exported)
            self.assertNotIn('?token', exported)

    def test_old_sidecar_is_excluded_even_if_recently_copied(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'client-game-bet-smoke.json').write_text(json.dumps({
                'scannedAt': '2026-09-06T03:00:30Z', 'executeBet': True, 'completedSpinCount': 99,
            }))
            result = self.build(root)
            self.assertEqual(result['highlights'][2]['value'], '未采集')
            self.assertNotIn('99', json.dumps(result))

    def test_no_run_never_attaches_sidecar(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'client-deposit-contract.json').write_text('{"depositRequest":true}')
            result = self.build(root, stats=False)
            self.assertEqual(result['highlights'][3]['value'], '未采集')
            self.assertEqual(result['images'], [])

    def test_external_image_path_is_not_linked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            outside = root / 'private.png'
            outside.write_bytes(b'private')
            os.utime(outside, (1788750030, 1788750030))
            (root / 'client-game-bet-smoke.json').write_text(json.dumps({
                'scannedAt': '2026-09-07T03:00:30Z', 'screenshots': {'before': str(outside)},
            }))
            self.assertEqual(self.build(root)['images'], [])


if __name__ == '__main__':
    unittest.main()
