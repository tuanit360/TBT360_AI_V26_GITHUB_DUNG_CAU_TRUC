import json
import tempfile
import unittest
from pathlib import Path

from app.worker_failure import (
    classify_worker_failure, read_safe_worker_failure
)


class WorkerFailureTests(unittest.TestCase):
    def test_cuda_failure_has_safe_code(self):
        result = classify_worker_failure(RuntimeError('CUDA driver not available'))
        self.assertEqual(result['code'], 'CUDA_UNAVAILABLE')
        self.assertNotIn('CUDA driver not available', str(result))

    def test_model_failure_identified(self):
        result = classify_worker_failure(RuntimeError('model_index.json missing'))
        self.assertEqual(result['code'], 'MODEL_MISSING')

    def test_report_never_echoes_untrusted_message(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'worker_failure.json'
            payload = classify_worker_failure(RuntimeError(
                'failed at C:\\Users\\private\\secret-token'))
            path.write_text(json.dumps(payload), encoding='utf-8')
            self.assertNotIn('secret-token', read_safe_worker_failure(path))

    def test_crash_without_report_is_actionable(self):
        with tempfile.TemporaryDirectory() as folder:
            output = read_safe_worker_failure(Path(folder) / 'absent.json')
            self.assertIn('không có báo cáo', output.lower())


if __name__ == '__main__':
    unittest.main()
