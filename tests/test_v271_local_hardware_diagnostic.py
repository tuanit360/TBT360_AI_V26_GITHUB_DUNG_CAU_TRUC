"""Ensure local diagnostics do not conflate shared GPU RAM with dedicated VRAM."""
import sys
import types
import unittest
from unittest.mock import patch

from training import local_hardware_diagnostic as diagnostic


class LocalHardwareDiagnosticTests(unittest.TestCase):
    def test_four_gib_t600_and_low_ram_are_reported(self):
        fake_torch = types.ModuleType('torch')
        fake_torch.cuda = types.SimpleNamespace(
            is_available=lambda: True,
            get_device_name=lambda index: 'NVIDIA T600 Laptop GPU',
            get_device_properties=lambda index: types.SimpleNamespace(
                total_memory=4 * 1024 ** 3,
            ),
        )
        with patch.dict(sys.modules, {'torch': fake_torch}):
            with patch.object(diagnostic, 'available_memory_gib', return_value=4.3):
                actual = diagnostic.inspect()
        self.assertEqual(actual['dedicated_vram_gib'], 4.0)
        self.assertEqual(actual['available_ram_gib'], 4.3)
        self.assertIn('Close memory-heavy', actual['recommendation'])
        self.assertFalse(actual['real_model_executed'])

    def test_diagnostic_never_claims_inference_on_cpu(self):
        fake_torch = types.ModuleType('torch')
        fake_torch.cuda = types.SimpleNamespace(is_available=lambda: False)
        with patch.dict(sys.modules, {'torch': fake_torch}):
            with patch.object(diagnostic, 'available_memory_gib', return_value=None):
                actual = diagnostic.inspect()
        self.assertFalse(actual['cuda_available'])
        self.assertFalse(actual['real_model_executed'])


if __name__ == '__main__':
    unittest.main()
