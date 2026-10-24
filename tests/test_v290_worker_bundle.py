import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from app.worker_diagnostic_bundle import make_worker_bundle
from app.worker_evidence import write_state


class WorkerDiagnosticBundleTests(unittest.TestCase):
    def test_redacts_logs_and_includes_state(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            logs = root / 'logs'
            logs.mkdir()
            write_state(root, '0123456789abcdef', 'FAILED', 'FAILED', 'MODEL_MISSING')
            (logs / 'image_worker.log').write_text(
                'token=private123\nTraceback sample\n', encoding='utf-8'
            )
            output = make_worker_bundle(root, job_id='0123456789abcdef')
            with ZipFile(output) as archive:
                self.assertIsNone(archive.testzip())
                content = archive.read('logs/image_worker.log').decode()
                self.assertNotIn('private123', content)
                self.assertIn('REDACTED_SECRET', content)
                self.assertIn('last_worker_state.json', archive.namelist())

    def test_missing_logs_still_generates_diagnostic(self):
        with tempfile.TemporaryDirectory() as folder:
            output = make_worker_bundle(folder)
            self.assertTrue(Path(output).is_file())


if __name__ == '__main__':
    unittest.main()
