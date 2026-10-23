"""Guard per-device pipeline caching when CPU fallback is selected."""
import unittest
from pathlib import Path


class DeviceCacheRegressionTests(unittest.TestCase):
    def test_cache_is_partitioned_by_device(self):
        source = (Path(__file__).resolve().parents[1] / 'app' /
                  'generate.py').read_text(encoding='utf-8')
        self.assertIn("cache_key = (memory_mode, 'cuda' if use_cuda else 'cpu')", source)
        self.assertIn('if cache_key in PIPELINES:', source)
        self.assertIn('PIPELINES[cache_key] = (pipe, placement)', source)
        self.assertNotIn('PIPELINES[memory_mode] =', source)

    def test_lora_state_follows_pipeline_device(self):
        source = (Path(__file__).resolve().parents[1] / 'app' /
                  'generate.py').read_text(encoding='utf-8')
        self.assertIn('device_key = (memory_mode, str(pipe.device))', source)
        self.assertIn('ACTIVE_LORA[device_key] = adapter_name', source)


if __name__ == '__main__':
    unittest.main()
