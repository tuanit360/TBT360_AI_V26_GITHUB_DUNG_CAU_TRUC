import tempfile
import unittest
from pathlib import Path
from app.worker_runtime_report import parent_report


class WorkerRuntimeTests(unittest.TestCase):
    def test_child_runtime_emits_structured_report(self):
        root = Path(__file__).resolve().parents[1]
        report = parent_report(root)
        self.assertTrue(report['worker_started'])
        self.assertIn('model_ready', report)
        self.assertFalse(report['inference_verified'])
        self.assertTrue((root / 'logs' / 'worker_runtime_v284.json').is_file())


if __name__ == '__main__':
    unittest.main()
