from support import ROOT, SCRIPTS
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from ui_business_visuals import visual_gallery


class VisualGalleryTests(unittest.TestCase):
    def test_only_same_run_unchanged_image_inside_screenshot_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'ui/results/screenshots'
            folder.mkdir(parents=True)
            image = folder / 'game-button-ready.png'
            image.write_bytes(b'original pixels')
            item = {'runId':'run', 'path':'ui/results/screenshots/game-button-ready.png', 'capturedAt':2000, 'sha256':hashlib.sha256(image.read_bytes()).hexdigest(), 'title':'ready', 'kind':'image assertion input'}
            state = {'runId':'run','startedAt':1,'finishedAt':3,'completed':[]}
            def render(value):
                (root / 'ui/results/game-round-state.json').write_text(json.dumps({'runId':'run','visualEvidence':{'ready':value}}))
                return visual_gallery(state, root)[0]
            self.assertEqual(len(render(item)), 1)
            for patch in [{'runId':'other'}, {'capturedAt':4000}, {'sha256':'modified'}, {'path':'../../outside.png'}]:
                self.assertEqual(render({**item, **patch}), [])
            image.write_bytes(b'replaced')
            self.assertEqual(render(item), [])

    def test_absent_images_are_explicit_not_fabricated(self):
        with tempfile.TemporaryDirectory() as directory:
            images, notes = visual_gallery({'completed': [], 'startedAt':1, 'finishedAt':3}, Path(directory))
            self.assertEqual(images, [])
            self.assertTrue(any('KYC' in note and '未保存' in note for note in notes))
