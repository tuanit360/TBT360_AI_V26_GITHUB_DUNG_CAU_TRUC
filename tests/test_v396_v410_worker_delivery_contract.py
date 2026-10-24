import hashlib
import tempfile
import unittest
from pathlib import Path
from PIL import Image

from app.worker_output_contract import (
    publish_selected_outputs, verify_worker_receipt, sha256_file, atomic_json,
)


class WorkerDeliveryTests(unittest.TestCase):
    def test_real_png_bytes_roundtrip_no_source_in_zip(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            job = parent / 'isolated_0123456789abcdef'
            job.mkdir()
            image = job / 'architecture_option_01_seed_1.png'
            Image.new('RGB', (512, 512), (100, 150, 180)).save(image)
            (job / 'reference_input.png').write_bytes(b'secret')
            (job / 'job.json').write_text('secret', encoding='utf-8')
            (job / 'generation.json').write_text('{}', encoding='utf-8')
            archive = publish_selected_outputs(
                job, job.with_suffix('.zip'),
                [image.name, 'generation.json'],
            )
            receipt = {
                'status': 'PASS_REAL_INFERENCE',
                'images': [[str(image), 'Generated']],
                'archive': str(archive),
                'sha256': sha256_file(archive),
            }
            atomic_json(job / 'worker_result.json', receipt)
            self.assertTrue(verify_worker_receipt(receipt, job))
            self.assertTrue((job / 'job.json').is_file())
            self.assertTrue((job / 'reference_input.png').is_file())
            image.write_bytes(b'corrupted')
            with self.assertRaises((ValueError, OSError)):
                verify_worker_receipt(receipt, job)


if __name__ == '__main__':
    unittest.main()
