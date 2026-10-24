import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from PIL import Image

from app.worker_output_contract import (
    atomic_json, publish_selected_outputs, verify_worker_receipt
)


class LargeWorkerStabilityBatchTests(unittest.TestCase):
    def test_verified_image_archive_without_private_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / 'isolated_test'
            folder.mkdir()
            (folder / 'reference_input.png').write_bytes(b'private')
            (folder / 'job.json').write_text('private', encoding='utf-8')
            image_path = folder / 'result.png'
            Image.new('RGB', (32, 32), (1, 2, 3)).save(image_path)
            (folder / 'generation.json').write_text('{"real": true}')
            archive = publish_selected_outputs(
                folder, folder.with_suffix('.zip'),
                ['result.png', 'generation.json']
            )
            with ZipFile(archive) as bundle:
                self.assertNotIn('job.json', bundle.namelist())
                self.assertNotIn('reference_input.png', bundle.namelist())
            receipt = {
                'status': 'PASS_REAL_INFERENCE',
                'archive': str(archive),
                'images': [[str(image_path), 'Generated']],
                'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
            }
            self.assertTrue(verify_worker_receipt(receipt, folder))
            receipt['sha256'] = 'incorrect'
            with self.assertRaisesRegex(ValueError, 'hash'):
                verify_worker_receipt(receipt, folder)
            self.assertTrue((folder / 'job.json').exists())

    def test_refuse_missing_and_duplicate_files(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / 'valid.txt').write_text('x')
            for names in [['missing.png'], ['valid.txt', 'valid.txt'],
                          ['../private.txt'], []]:
                with self.assertRaises(ValueError):
                    publish_selected_outputs(folder, folder / 'result.zip', names)
            self.assertFalse((folder / 'result.zip').exists())

    def test_receipt_atomic_json_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'receipt.json'
            atomic_json(target, {'status': 'OK', 'message': 'Ảnh hợp lệ'})
            self.assertEqual(json.loads(target.read_text(encoding='utf-8'))['message'], 'Ảnh hợp lệ')
            self.assertFalse(list(Path(temp).glob('*.part')))


if __name__ == '__main__':
    unittest.main()
