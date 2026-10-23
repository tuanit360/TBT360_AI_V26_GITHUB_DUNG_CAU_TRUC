import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from app.image_generation_contract import image_generation_contract


class ImageGenerationContractTests(unittest.TestCase):
    def test_offline_missing_model_returns_log_and_no_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('app.local_workspace.record_operation'):
                result = image_generation_contract(
                    directory, lambda *args, **kwargs: self.fail('called'),
                    (), offline=True, readiness={'model_files_complete': False},
                )
            self.assertEqual(len(result), 4)
            self.assertIsNone(result[1])
            self.assertIn('BLOCKED_MISSING_MODEL', result[3])

    def test_exception_returns_copyable_failure_log(self):
        with tempfile.TemporaryDirectory() as directory:
            def failing(*args, **kwargs):
                raise RuntimeError('CUDA out of memory')
            with patch('app.local_workspace.record_operation'), patch(
                'app.image_generation_contract.logging.getLogger'
            ) as mocked_logger:
                result = image_generation_contract(directory, failing, ())
                mocked_logger.return_value.exception.assert_called_once()
            self.assertEqual(len(result), 4)
            self.assertIsNone(result[1])
            self.assertIn('bộ nhớ', result[2])
            self.assertIn('FAIL | RuntimeError', result[3])

    def test_success_renders_image_and_keeps_zip(self):
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / 'render.png'
            Image.new('RGB', (128, 96)).save(image_path)
            archive = Path(directory) / 'render.zip'
            archive.write_bytes(b'example')
            def success(*args, **kwargs):
                return [(str(image_path), 'Ảnh thử')], str(archive), 'Đã tạo'
            with patch('app.local_workspace.record_operation'):
                result = image_generation_contract(directory, success, ())
            self.assertIn('data:image/png;base64,', result[0])
            self.assertEqual(result[1], str(archive))
            self.assertIn('PASS', result[3])


if __name__ == '__main__':
    unittest.main()
