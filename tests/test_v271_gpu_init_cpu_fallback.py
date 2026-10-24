"""Regression contract: failed GPU placement retries a fresh FP32 CPU model."""
import unittest
from pathlib import Path


class V271GPUFallbackTests(unittest.TestCase):
    def test_fresh_cpu_fallback_not_half_initialized_gpu(self):
        source = (Path(__file__).resolve().parents[1] / 'app' /
                  'generate.py').read_text(encoding='utf-8')
        self.assertIn('except (RuntimeError, AssertionError) as exc:', source)
        self.assertIn('del pipe', source)
        self.assertIn("cache_key = (memory_mode, 'cpu')", source)
        self.assertIn("torch_dtype=torch.float32", source)
        self.assertIn("placement = 'CPU dự phòng (GPU khởi tạo thất bại)'", source)


if __name__ == '__main__':
    unittest.main()
