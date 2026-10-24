import tempfile
import unittest
from pathlib import Path
from app.worker_transport_smoke import parent_probe


class WorkerTransportSmokeTests(unittest.TestCase):
    def test_real_subprocess_exchanges_png_zip_and_sha(self):
        root = Path(__file__).resolve().parents[1]
        report = parent_probe(root)
        self.assertEqual(report['status'], 'PASS_TRANSPORT_ONLY')


if __name__ == '__main__':
    unittest.main()
