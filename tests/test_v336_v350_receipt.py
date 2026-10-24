import tempfile
import unittest
from pathlib import Path
from PIL import Image
from app.worker_output_contract import (
    publish_selected_outputs, verify_worker_receipt, sha256_file,
)


class ReceiptTests(unittest.TestCase):
    def test_valid_and_extra_member(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / 'job'
            folder.mkdir()
            png = folder / 'image.png'
            Image.new('RGB', (160, 160), (20, 80, 150)).save(png)
            (folder / 'generation.json').write_text('{}', encoding='utf-8')
            (folder / 'unexpected.txt').write_text('extra', encoding='utf-8')
            def receipt(names):
                archive = publish_selected_outputs(
                    folder, root / 'job.zip', names,
                )
                return {
                    'status': 'PASS_REAL_INFERENCE',
                    'archive': str(archive),
                    'sha256': sha256_file(archive),
                    'images': [[str(png), 'Test']],
                }
            good = receipt(['image.png', 'generation.json'])
            self.assertTrue(verify_worker_receipt(good, folder))
            extra = receipt(['image.png', 'generation.json', 'unexpected.txt'])
            with self.assertRaisesRegex(ValueError, 'unexpected files'):
                verify_worker_receipt(extra, folder)


if __name__ == '__main__':
    unittest.main()
