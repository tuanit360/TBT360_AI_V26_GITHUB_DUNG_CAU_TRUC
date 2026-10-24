import unittest
from types import SimpleNamespace
from app.runtime_readiness import check_generation_runtime
from app.generation_failures import explain_generation_failure


class CPUPreflightTests(unittest.TestCase):
    def test_cpu_wheel_uses_cpu_without_cuda(self):
        fake = SimpleNamespace(
            version=SimpleNamespace(cuda=None),
            cuda=SimpleNamespace(is_available=lambda: False),
        )
        result = check_generation_runtime(fake, environ={}, free_ram_gib=12)
        self.assertEqual(result['device'], 'cpu')
        self.assertTrue(result['ready'])

    def test_low_ram_refused_without_diffusers(self):
        fake = SimpleNamespace(
            version=SimpleNamespace(cuda=None),
            cuda=SimpleNamespace(is_available=lambda: False),
        )
        result = check_generation_runtime(fake, environ={}, free_ram_gib=3)
        self.assertFalse(result['ready'])
        self.assertEqual(result['device'], 'none')
        self.assertIn('BIMAI360_CPU_RAM_LOW', result['message'])
        self.assertIn('RAM', explain_generation_failure(RuntimeError(result['message'])))

    def test_no_false_cuda_driver_advice_for_cpu_preflight(self):
        reason = explain_generation_failure(
            RuntimeError('BIMAI360_CPU_RAM_LOW: low memory')
        )
        self.assertNotIn('trình điều khiển NVIDIA', reason)


if __name__ == '__main__':
    unittest.main()
