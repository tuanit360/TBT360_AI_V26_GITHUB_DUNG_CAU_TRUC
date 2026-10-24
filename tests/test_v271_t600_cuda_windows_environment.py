"""Prevent shipping a CPU-only Python path as the NVIDIA T600 CUDA launcher."""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WindowsT600CudaEnvironmentTests(unittest.TestCase):
    def test_cuda_env_is_separate_from_cpu_portable(self):
        setup = (ROOT / 'SETUP_T600_CUDA_WINDOWS.bat').read_text('utf-8')
        self.assertIn('py -3.11 -m venv .venv-t600-cuda', setup)
        self.assertIn('https://download.pytorch.org/whl/cu121', setup)
        self.assertIn('torch.cuda.is_available()', setup)
        self.assertIn('if errorlevel 1 goto :fail', setup)
        self.assertNotIn('download.pytorch.org/whl/cpu', setup)

    def test_both_launchers_use_cuda_venv_and_preserve_failures(self):
        for path in ('RUN_REAL_T600_LOCAL_WINDOWS.bat',
                     'RUN_T600_INFERENCE_ONLY_WINDOWS.bat'):
            with self.subTest(path=path):
                data = (ROOT / path).read_text('utf-8')
                self.assertIn('set "PY=.venv-t600-cuda\\Scripts\\python.exe"', data)
                self.assertIn('if not exist "%PY%" goto :environment_missing', data)
                self.assertIn('"%PY%" -m training.smoke_diffusers_inference', data)
                self.assertIn(':environment_missing', data)
                self.assertIn(':fail', data)
                self.assertNotIn('\npython -m training.run_lora', data)


if __name__ == '__main__':
    unittest.main()
