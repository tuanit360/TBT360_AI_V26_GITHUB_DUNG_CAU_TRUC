import unittest
from types import SimpleNamespace
from unittest.mock import patch
from app.runtime_selection import inspect_runtime, require_cpu_memory


def fake_torch(cuda_version=None, available=False, vram=4 * 1024**3):
    return SimpleNamespace(
        version=SimpleNamespace(cuda=cuda_version),
        cuda=SimpleNamespace(
            is_available=lambda: available,
            get_device_properties=lambda index: SimpleNamespace(total_memory=vram),
        ),
    )


class RuntimeSelectionTests(unittest.TestCase):
    def test_cpu_torch_never_offers_cuda_even_if_gpu_exists(self):
        info = inspect_runtime(fake_torch(None, True), environ={},
                               free_ram_gib=12)
        self.assertEqual(info['mode'], 'cpu')
        self.assertFalse(info['cuda_available'])

    def test_gpu_with_cuda_torch_can_run(self):
        info = inspect_runtime(fake_torch('12.1', True), environ={},
                               free_ram_gib=3)
        self.assertEqual(info['mode'], 'cuda')
        self.assertEqual(info['gpu_vram_gib'], 4.0)

    def test_forced_cpu_still_requires_ram(self):
        info = inspect_runtime(fake_torch('12.1', True),
                               environ={'BIMAI360_FORCE_CPU': '1'},
                               free_ram_gib=4)
        self.assertEqual(info['mode'], 'blocked')

    def test_no_cuda_and_low_ram_blocks_before_model_load(self):
        info = inspect_runtime(fake_torch(), environ={}, free_ram_gib=3)
        self.assertEqual(info['mode'], 'blocked')

    def test_gpu_initialization_fallback_rechecks_ram(self):
        with patch('app.runtime_selection.available_ram_gib', return_value=3):
            with self.assertRaisesRegex(RuntimeError, 'Không đủ RAM'):
                require_cpu_memory()


if __name__ == '__main__':
    unittest.main()
