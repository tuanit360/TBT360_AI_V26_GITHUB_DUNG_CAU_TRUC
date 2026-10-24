import json
import tempfile
import unittest
from pathlib import Path
from app.worker_retry import should_retry_cpu


class RetryTests(unittest.TestCase):
    def test_retry_only_cuda(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'failure.json'
            for code, expected in [('CUDA_UNAVAILABLE', True),
                                   ('MODEL_MISSING', False),
                                   ('OUT_OF_MEMORY', False)]:
                path.write_text(json.dumps({
                    'schema': 'bimai360.worker_failure.v1',
                    'status': 'FAILED', 'code': code,
                }), encoding='utf-8')
                self.assertEqual(should_retry_cpu(path, {}), expected)
                self.assertFalse(should_retry_cpu(
                    path, {'BIMAI360_FORCE_CPU': '1'}))


if __name__ == '__main__':
    unittest.main()
