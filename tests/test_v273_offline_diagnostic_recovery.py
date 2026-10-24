import tempfile
import unittest
import zipfile
from pathlib import Path
from app.diagnostic_bundle import build_diagnostic_zip


class OfflineDiagnosticsRecoveryTests(unittest.TestCase):
    def test_bundle_captures_console_when_web_callbacks_are_broken(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / 'logs').mkdir()
            (root / 'logs' / 'startup_console.log').write_text(
                'Unhandled callback exception\n', encoding='utf-8'
            )
            archive = build_diagnostic_zip(root)
            with zipfile.ZipFile(archive) as package:
                self.assertIn('logs/startup_console.log', package.namelist())
                self.assertIn('Unhandled callback exception',
                              package.read('logs/startup_console.log').decode('utf-8'))

    def test_offline_launcher_never_uses_gradio_or_browser(self):
        root = Path(__file__).resolve().parents[1]
        launcher = (root / 'EXPORT_DIAGNOSTICS_OFFLINE_WINDOWS.bat').read_text(
            encoding='utf-8'
        )
        self.assertIn('--diagnostics', launcher)
        self.assertNotIn('http://', launcher)


if __name__ == '__main__':
    unittest.main()
