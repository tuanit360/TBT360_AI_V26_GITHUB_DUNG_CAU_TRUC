"""CPU-only PyTorch must not be reported as a broken NVIDIA driver."""
import unittest
from app.generation_failures import explain_generation_failure


class CPUCudaFailureMessageTests(unittest.TestCase):
    def test_cpu_only_torch_has_actionable_message(self):
        for message in (
            'Torch not compiled with CUDA enabled',
            'CUDA is not available in this build',
            'PyTorch was compiled without CUDA support',
        ):
            with self.subTest(message=message):
                result = explain_generation_failure(ValueError(message))
                self.assertIn('PyTorch CPU', result)
                self.assertIn('T600', result)
                self.assertNotIn('Kiểm tra trình điều khiển NVIDIA', result)


if __name__ == '__main__':
    unittest.main()
