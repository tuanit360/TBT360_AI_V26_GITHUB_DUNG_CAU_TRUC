import hashlib
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from PIL import Image
from app.worker_output_contract import publish_selected_outputs, verify_worker_receipt


class WorkerHardeningTests(unittest.TestCase):
    def test_reject_archive_outside_expected_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / 'job'
            folder.mkdir()
            (folder / 'data.txt').write_text('x', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'sibling'):
                publish_selected_outputs(
                    folder, root / 'unrelated' / 'archive.zip', ['data.txt'])

    def test_reject_unexpected_second_png(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / 'job'
            folder.mkdir()
            image = folder / 'image.png'
            second = folder / 'other.png'
            Image.new('RGB', (64, 64), (10, 90, 120)).save(image)
            Image.new('RGB', (64, 64), (40, 70, 100)).save(second)
            archive = publish_selected_outputs(
                folder, root / 'job.zip', ['image.png', 'other.png'])
            report = {
                'status': 'PASS_REAL_INFERENCE',
                'archive': str(archive),
                'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                'images': [[str(image), 'one']],
            }
            with self.assertRaisesRegex(ValueError, 'Unexpected PNG'):
                verify_worker_receipt(report, folder)

    def test_refuse_large_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / 'job'
            folder.mkdir()
            for index in range(7):
                (folder / f'{index}.txt').write_text('x', encoding='utf-8')
            with self.assertRaises(ValueError):
                publish_selected_outputs(
                    folder, Path(temp) / 'job.zip',
                    [f'{index}.txt' for index in range(7)],
                )


if __name__ == '__main__':
    unittest.main()
