import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image

from app.dataset_import import import_images, preview_project


class DatasetImportTests(unittest.TestCase):
    def test_import_preview_and_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'sample.png'
            Image.new('RGB', (300, 300), 'white').save(source)
            first = import_images(root, [source], 'office_01', 'Office facade, white exterior')
            self.assertEqual(first['imported'], 1)
            self.assertFalse(first['training_started'])
            images, report = preview_project(root, 'office_01')
            self.assertEqual(len(images), 1)
            self.assertEqual(report['pending_review'], 1)
            second = import_images(root, [source], 'office_01', 'Office facade, white exterior')
            self.assertEqual(second['imported'], 0)
            self.assertEqual(len(second['skipped']), 1)

    def test_invalid_project_and_small_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'tiny.png'
            Image.new('RGB', (32, 32), 'white').save(source)
            with self.assertRaises(ValueError):
                import_images(root, [source], '../wrong', 'Valid image caption')
            result = import_images(root, [source], 'office_02', 'Valid image caption')
            self.assertEqual(result['imported'], 0)
            self.assertTrue(result['skipped'])

    def test_saved_label_is_pending_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'sample.jpg'
            Image.new('RGB', (300, 310), 'blue').save(source)
            import_images(root, [source], 'tower_01', 'Blue office facade test')
            row = json.loads((root / 'dataset/raw/tower_01/import_manifest.jsonl').read_text().strip())
            self.assertEqual(row['review_status'], 'NEEDS_REVIEW')
            self.assertIn('sha256_pixels', row)
