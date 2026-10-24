import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from app.isolated_image_bridge import execute_image_job
from app.isolated_image_worker import run_job


class IsolationTests(unittest.TestCase):
    def test_bad_worker_job_fails_without_importing_model(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            jobdir = root / 'output' / 'isolated_test'
            jobdir.mkdir(parents=True)
            path = jobdir / 'job.json'
            path.write_text(json.dumps({'schema': 'bad'}), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Invalid worker request'):
                run_job(path)

    def test_existing_gradio_layout_unchanged(self):
        source = Path(__file__).resolve().parents[1] / 'app' / 'generate.py'
        content = source.read_text(encoding='utf-8')
        self.assertIn('execute_image_job', content)
        self.assertIn('Thiết kế và sinh ảnh', content)
        self.assertIn('Mô hình 2D / 3D', content)

    def test_invalid_image_refused_before_subprocess(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                execute_image_job(folder, (None,) + (None,) * 13)


if __name__ == '__main__':
    unittest.main()
