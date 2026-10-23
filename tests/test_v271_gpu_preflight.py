"""CPU CI verifies GPU preflight fails safely without claiming GPU work."""
import unittest
import types
import sys
from unittest.mock import patch

from training.preflight_real_gpu import check_gpu_environment


class RealGPUPreflightTests(unittest.TestCase):
    def test_missing_dependency_fails_closed(self):
        original = __import__
        def unavailable(name, *args, **kwargs):
            if name == 'diffusers':
                raise ImportError('fixture missing diffusers')
            return original(name, *args, **kwargs)
        with patch('importlib.import_module', side_effect=unavailable):
            result = check_gpu_environment()
        self.assertFalse(result['ready'])
        self.assertIn('diffusers unavailable', result['reason'])

    def test_low_vram_rejected_before_dataset_verification(self):
        fake_torch = types.ModuleType('torch')
        fake_torch.cuda = types.SimpleNamespace(
            is_available=lambda: True,
            get_device_properties=lambda index: types.SimpleNamespace(
                total_memory=4 * 1024 ** 3
            ),
        )
        with patch.dict(sys.modules, {'torch': fake_torch}):
            with patch('importlib.import_module', return_value=fake_torch):
                result = check_gpu_environment()
        self.assertFalse(result['ready'])
        self.assertIn('VRAM', result['reason'])

    def test_workflow_requires_preflight_before_training(self):
        from pathlib import Path
        yml = (Path(__file__).resolve().parents[1] /
               '.github' / 'workflows' / 'gpu-train.yml').read_text('utf-8')
        self.assertLess(
            yml.index('python -m training.preflight_real_gpu'),
            yml.index('python -m training.run_lora'),
        )


if __name__ == '__main__':
    unittest.main()
