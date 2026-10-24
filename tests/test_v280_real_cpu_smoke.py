import inspect
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.smoke_real_image_inference import run


class V280CPURealSmokeTests(unittest.TestCase):
    def test_cpu_mode_explicitly_supported(self):
        self.assertIn('device', inspect.signature(run).parameters)

    def test_missing_checkpoint_cannot_report_success(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError, 'checkpoint'):
                run(Path(folder) / 'missing', Path(folder) / 'output', 'cpu')
            self.assertFalse((Path(folder) / 'output' / 'real_inference_report.json').exists())

    def test_launcher_is_cpu_only(self):
        root = Path(__file__).resolve().parents[1]
        content = (root / 'START_V280_CPU_REAL_IMAGE_TEST.bat').read_text()
        self.assertIn('--device cpu', content)
        self.assertIn('v280_cpu_smoke.log', content)


if __name__ == '__main__':
    unittest.main()
