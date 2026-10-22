import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from PIL import Image

from app.dataset_bundle import import_v81_bundle
from app.dataset_import import preview_all_projects


class V81DatasetBundleTests(unittest.TestCase):
    def _archive(self, root, *, tamper=False):
        image = Image.new('RGB', (300, 340), '#c4dceb')
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=87, subsampling=0)
        raw = output.getvalue()
        with Image.open(io.BytesIO(raw)) as reloaded:
            pixels = reloaded.convert('RGB').tobytes()
        pixel_hash = hashlib.sha256(pixels).hexdigest()
        record = {
            'file_name': pixel_hash[:24] + '.jpg',
            'sha256_pixels': '0' * 64 if tamper else pixel_hash,
            'project_id': 'sample_office_01',
            'caption': 'Architectural reference, draft label',
            'review_status': 'NEEDS_REVIEW',
        }
        path = root / 'prepared_v81.zip'
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('dataset/USER_DATASET_MANIFEST.json', json.dumps({
                'schema': 'tbt360_v81_architecture_raster_sample_v1',
                'project_summary': [{'project_id': 'sample_office_01', 'imported_images': 1}],
            }))
            archive.writestr('dataset/raw/sample_office_01/import_manifest.jsonl', json.dumps(record) + '\n')
            archive.writestr('dataset/raw/sample_office_01/' + record['file_name'], raw)
        return path

    def test_one_click_preserves_project_group_and_detects_repeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = self._archive(root)
            first = import_v81_bundle(root, archive)
            self.assertEqual(first['new_images'], 1)
            self.assertFalse(first['training_started'])
            gallery, report = preview_all_projects(root)
            self.assertEqual(len(gallery), 1)
            self.assertEqual(report['projects'], 1)
            self.assertEqual(report['pending_review'], 1)
            second = import_v81_bundle(root, archive)
            self.assertEqual(second['new_images'], 0)
            self.assertEqual(second['already_imported'], 1)

    def test_bad_pixel_hash_prevents_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = self._archive(root, tamper=True)
            with self.assertRaises(ValueError):
                import_v81_bundle(root, archive)
            self.assertFalse((root / 'dataset').exists())
