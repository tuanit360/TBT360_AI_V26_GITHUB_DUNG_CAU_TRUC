import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from app.dataset_auto_import import inspect_archive, import_any_zip


class SmartZipTests(unittest.TestCase):
    def make_image_zip(self, root):
        pic = root / 'office.png'
        Image.new('RGB', (320, 320), '#adcdee').save(pic)
        inner = root / 'images.zip'
        with zipfile.ZipFile(inner, 'w') as bundle:
            bundle.write(pic, 'floor1/office.png')
        return inner

    def test_accept_ordinary_image_zip(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pack = self.make_image_zip(root)
            result = import_any_zip(root, pack, 'office_82', 'Facade and floor sample image')
            self.assertEqual(result['imported'], 1)
            self.assertFalse(result['training_started'])
            self.assertEqual(result['detected_package'], 'images')

    def test_nested_artifact_zip(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inner = self.make_image_zip(root)
            outer = root / 'github_artifact.zip'
            with zipfile.ZipFile(outer, 'w') as archive:
                archive.write(inner, 'TBT360_V82_DATASET.zip')
            result = import_any_zip(root, outer, 'office_82', 'Facade and floor sample image')
            self.assertEqual(result['imported'], 1)
            self.assertEqual(result['detected_package'], 'wrapped_images')

    def test_invalid_or_empty_zip_error_is_clear(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'empty.zip'
            with zipfile.ZipFile(path, 'w') as pack:
                pack.writestr('README.txt', 'No images here')
            with self.assertRaisesRegex(ValueError, 'Không tìm thấy ảnh'):
                inspect_archive(path)
