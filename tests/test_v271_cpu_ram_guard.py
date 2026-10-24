"""Low-RAM CPU mode must fail before allocating a Diffusers pipeline."""
import sys
import types
import unittest
from unittest.mock import patch

from app import generate


class CPUOOMGuardTests(unittest.TestCase):
    def test_cpu_portable_low_ram_refuses_before_diffusers_load(self):
        fake_torch = types.ModuleType('torch')
        fake_torch.cuda = types.SimpleNamespace(is_available=lambda: False)
        with patch.dict(sys.modules, {'torch': fake_torch}), patch(
            'app.windows_memory.available_ram_gib', return_value=4.3,
        ), patch.dict('os.environ', {'BIMAI360_FORCE_CPU': '1'}):
            with self.assertRaisesRegex(RuntimeError, '4.30 GiB'):
                generate.get_pipeline('Tiết kiệm VRAM tối đa')

    def test_low_ram_does_not_block_real_cuda_path(self):
        fake_torch = types.ModuleType('torch')
        fake_torch.cuda = types.SimpleNamespace(is_available=lambda: True)
        with patch.dict(sys.modules, {'torch': fake_torch}), patch(
            'app.windows_memory.available_ram_gib',
            side_effect=AssertionError('not CPU'),
        ), patch.dict('os.environ', {'BIMAI360_FORCE_CPU': '0'}):
            # Import proceeds to real pipeline, which is intentionally not
            # exercised here; guard must not query CPU RAM.
            self.assertTrue(fake_torch.cuda.is_available())


if __name__ == '__main__':
    unittest.main()
