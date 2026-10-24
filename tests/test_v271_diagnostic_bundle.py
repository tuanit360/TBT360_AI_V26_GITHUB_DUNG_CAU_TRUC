import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from app.diagnostic_bundle import build_diagnostic_zip


class DiagnosticBundleTests(unittest.TestCase):
    def test_offline_diagnostics_redact_and_exclude_private_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            logs = root / 'logs'
            logs.mkdir()
            (logs / 'runtime_errors.log').write_text(
                'RuntimeError token=SECRET123 at C:\\Users\\Alice\\private.txt\n',
                encoding='utf-8',
            )
            (root / 'secret_image.png').write_bytes(b'PRIVATE_IMAGE')
            (root / 'models').mkdir()
            (root / 'models' / 'weights.safetensors').write_bytes(b'WEIGHTS')
            path = build_diagnostic_zip(root)
            with zipfile.ZipFile(path) as package:
                names = package.namelist()
                self.assertIn('diagnostic_summary.json', names)
                self.assertIn('logs/runtime_errors.log', names)
                self.assertFalse(any(name.endswith('.png') for name in names))
                self.assertFalse(any(name.endswith('.safetensors') for name in names))
                payload = package.read('logs/runtime_errors.log').decode()
                self.assertNotIn('SECRET123', payload)
                self.assertNotIn('Alice', payload)
                summary = json.loads(package.read('diagnostic_summary.json'))
                self.assertEqual(summary['version'], 'V271')

    def test_missing_logs_still_produces_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            path = build_diagnostic_zip(directory)
            with zipfile.ZipFile(path) as package:
                self.assertIn('diagnostic_summary.json', package.namelist())


if __name__ == '__main__':
    unittest.main()
