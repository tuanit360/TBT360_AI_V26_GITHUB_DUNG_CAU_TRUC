import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from PIL import Image

from app.worker_output_contract import (
    publish_selected_outputs, verify_worker_receipt, sha256_file, streams_match
)
from app.diagnostic_image_render import render_image_gallery


class WorkerStreamingRegression(unittest.TestCase):
    def test_streaming_file_sha_matches_standard(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'blob.dat'
            path.write_bytes(b'a' * (1024 * 1024 + 5))
            self.assertEqual(sha256_file(path), hashlib.sha256(path.read_bytes()).hexdigest())

    def test_stream_comparison(self):
        self.assertTrue(streams_match(io.BytesIO(b'hello'), io.BytesIO(b'hello')))
        self.assertFalse(streams_match(io.BytesIO(b'hello'), io.BytesIO(b'hella')))

    def test_real_png_zip_roundtrip(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root) / 'isolated_test'
            folder.mkdir()
            image = folder / 'generated.png'
            Image.new('RGB', (512, 512), (130, 150, 60)).save(image)
            (folder / 'generation.json').write_text('{"test": true}', encoding='utf-8')
            archive = publish_selected_outputs(folder, Path(root) / 'isolated_test.zip',
                                                ['generated.png', 'generation.json'])
            receipt = {'status': 'PASS_REAL_INFERENCE',
                       'archive': str(archive), 'sha256': sha256_file(archive),
                       'images': [[str(image), 'Test']]}
            self.assertTrue(verify_worker_receipt(receipt, folder))
            rendered = render_image_gallery(receipt['images'])
            self.assertIn('data:image/png;base64,', rendered)


if __name__ == '__main__':
    unittest.main()
