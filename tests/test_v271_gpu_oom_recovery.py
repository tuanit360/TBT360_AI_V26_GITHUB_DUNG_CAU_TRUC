"""Static regression for GPU OOM cache invalidation and explicit retry."""
import unittest
from pathlib import Path


class GPUOutOfMemoryRecoveryTests(unittest.TestCase):
    def test_cuda_cache_is_evicted_after_oom(self):
        source = (Path(__file__).resolve().parents[1] / 'app' /
                  'generate.py').read_text(encoding='utf-8')
        self.assertIn('except torch.cuda.OutOfMemoryError as exc:', source)
        self.assertIn("if key[1] == 'cuda':", source)
        self.assertIn('failed_pipe, _ = PIPELINES.pop(key)', source)
        self.assertIn('ACTIVE_LORA.pop(id(failed_pipe), None)', source)
        self.assertIn('GPU_DISABLED_FOR_SESSION = True', source)
        self.assertIn('Lần thử tiếp theo sẽ dùng CPU', source)


if __name__ == '__main__':
    unittest.main()
