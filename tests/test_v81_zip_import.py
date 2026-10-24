import tempfile
import unittest
import zipfile
from pathlib import Path
from PIL import Image

from app.dataset_zip_import import import_zip_archive


class V81ZipImportTests(unittest.TestCase):
    def test_archive_import_and_deduplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample = root / 'sample.png'
            Image.new('RGB', (300, 300), '#aaccee').save(sample)
            archive = root / 'images.zip'
            with zipfile.ZipFile(archive, 'w') as output:
                output.write(sample, 'office/front.png')
                output.write(sample, '../untrusted/front.png')
            first = import_zip_archive(root, archive, 'office_81', 'Office building front elevation')
            self.assertEqual(first['imported'], 1)
            self.assertEqual(first['skipped'], 1)
            second = import_zip_archive(root, archive, 'office_81', 'Office building front elevation')
            self.assertEqual(second['imported'], 0)
            self.assertFalse((root / 'untrusted').exists())
            self.assertFalse(first['training_started'])

    def test_reject_invalid_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / 'empty.zip'
            with zipfile.ZipFile(archive, 'w'):
                pass
            with self.assertRaises(ValueError):
                import_zip_archive(tmp, archive, '../bad', 'Architecture reference set')
