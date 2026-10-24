"""Offline error evidence remains available when Gradio callbacks disconnect."""
import unittest
from pathlib import Path

from app.diagnostic_bundle import ALLOWED_LOGS

ROOT = Path(__file__).resolve().parents[1]


class OfflineLogFallbackTests(unittest.TestCase):
    def test_console_log_in_diagnostic_bundle(self):
        self.assertIn('console_errors.log', ALLOWED_LOGS)

    def test_bat_launch_captures_stderr_without_gradio(self):
        source = (ROOT / 'CHAY_BIMAI360_GHI_LOG_LOI.bat').read_text('utf-8')
        self.assertIn('2>&1', source)
        self.assertIn('BIMAI360.exe" --diagnostics', source)
        self.assertIn('notepad "logs\\console_errors.log"', source)
        self.assertNotIn('gradio_api', source)

    def test_build_and_portable_verifier_include_fallback_launcher(self):
        filename = 'CHAY_BIMAI360_GHI_LOG_LOI.bat'
        self.assertIn(filename, (ROOT / 'tools' / 'build_release.py').read_text('utf-8'))
        verifier = (ROOT / 'tools' / 'verify_portable.py').read_text('utf-8')
        self.assertGreaterEqual(verifier.count(filename), 2)


if __name__ == '__main__':
    unittest.main()
