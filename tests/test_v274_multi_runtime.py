import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.runtime_preflight import probe


class V274MultiRuntimeTests(unittest.TestCase):
    def test_basic_preflight_writes_no_ai_import(self):
        with tempfile.TemporaryDirectory() as directory:
            report = probe(directory, 'cpu', 0)
            self.assertEqual(report['schema'], 'bimai360.preflight.v274')
            self.assertIn('ready', report)
            self.assertIn('filesystem', [x['name'] for x in report['checks']])
            json.dumps(report)

    def test_missing_cuda_driver_blocks_cuda_only(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('tools.runtime_preflight.shutil.which', return_value=None):
                cuda = probe(directory, 'cuda', 0)
                cpu = probe(directory, 'cpu', 0)
            self.assertFalse(cuda['ready'])
            self.assertTrue(cpu['ready'])
            self.assertIn('nvidia_smi', [x['name'] for x in cuda['checks']])

    def test_runtime_launchers_are_separate(self):
        root = Path(__file__).resolve().parents[1]
        venv = (root / 'START_BIMAI360_VENV.bat').read_text()
        safe = (root / 'START_BIMAI360_SAFE_DIAGNOSTICS.bat').read_text()
        self.assertIn('-m tools.runtime_preflight', venv)
        self.assertIn('--diagnostics', safe)
        self.assertNotIn('run_portable.py >', safe)


if __name__ == '__main__':
    unittest.main()
