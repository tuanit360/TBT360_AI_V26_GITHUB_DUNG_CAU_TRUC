import tempfile
import unittest
import zipfile
from pathlib import Path
from app.atomic_export import publish_directory_zip


class AtomicExportTests(unittest.TestCase):
    def test_export_contains_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            src = root / 'images'
            src.mkdir()
            (src / 'image.txt').write_text('image', encoding='utf-8')
            archive = publish_directory_zip(src, root / 'images.zip')
            with zipfile.ZipFile(archive) as package:
                self.assertEqual(package.read('image.txt'), b'image')

    def test_empty_source_preserves_previous_zip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            src = root / 'empty'
            src.mkdir()
            dest = root / 'images.zip'
            dest.write_bytes(b'previous')
            with self.assertRaises(ValueError):
                publish_directory_zip(src, dest)
            self.assertEqual(dest.read_bytes(), b'previous')


if __name__ == '__main__':
    unittest.main()
