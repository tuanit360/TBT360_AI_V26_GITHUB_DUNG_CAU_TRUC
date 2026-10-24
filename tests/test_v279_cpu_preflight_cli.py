import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.cpu_generation_preflight import build_cpu_preflight_report


class V279CPUPreflightTests(unittest.TestCase):
    def setUp(self):
        self.torch = types.SimpleNamespace(float32=object(), Generator=object())

    def test_ram_blocked_before_model_load(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict('os.environ', {'TBT360_OFFLINE': '0'}):
                report = build_cpu_preflight_report(
                    folder, torch_module=self.torch, free_ram_gib=3.1
                )
            self.assertFalse(report['ready'])
            self.assertFalse(report['ram_ok'])
            self.assertIn('RAM', ' '.join(report['issues']))

    def test_offline_missing_model_blocked(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict('os.environ', {'TBT360_OFFLINE': '1'}):
                report = build_cpu_preflight_report(
                    folder, torch_module=self.torch, free_ram_gib=12
                )
            self.assertFalse(report['ready'])
            self.assertFalse(report['local_model_ready'])

    def test_online_missing_model_is_warning_not_successful_inference(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict('os.environ', {'TBT360_OFFLINE': '0'}):
                report = build_cpu_preflight_report(
                    folder, torch_module=self.torch, free_ram_gib=12
                )
            self.assertTrue(report['ready'])
            self.assertFalse(report['local_model_ready'])
            self.assertIn('no inference', report['note'])

    def test_runner_exposes_offline_preflight(self):
        runner = (Path(__file__).resolve().parents[1] / 'run_portable.py').read_text()
        self.assertIn("'--cpu-preflight'", runner)
        self.assertIn('cpu_preflight.json', runner)


if __name__ == '__main__':
    unittest.main()
