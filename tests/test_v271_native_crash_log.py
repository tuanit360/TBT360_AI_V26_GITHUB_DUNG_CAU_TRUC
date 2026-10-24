"""Fatal Python tracebacks must remain accessible without Gradio callbacks."""
import unittest
from pathlib import Path

from app.diagnostic_bundle import ALLOWED_LOGS


class FatalCrashEvidenceTests(unittest.TestCase):
    def test_native_fatal_log_is_in_offline_bundle(self):
        self.assertIn('python_fatal.log', ALLOWED_LOGS)

    def test_fatal_handler_enabled_on_portable_start(self):
        source = (
            Path(__file__).resolve().parents[1] / 'run_portable.py'
        ).read_text(encoding='utf-8')
        self.assertIn("faulthandler.enable(file=crash_stream, all_threads=True)", source)
        self.assertIn("'python_fatal.log'", source)


if __name__ == '__main__':
    unittest.main()
