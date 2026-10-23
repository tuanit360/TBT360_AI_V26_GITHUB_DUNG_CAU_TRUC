"""Functional GPU OOM cache invalidation regression."""
import unittest
from app import generate


class GPUOutOfMemoryRecoveryTests(unittest.TestCase):
    def test_evicts_only_cuda_pipelines_and_associated_lora(self):
        old_pipelines = generate.PIPELINES
        old_lora = generate.ACTIVE_LORA
        old_disabled = generate.GPU_DISABLED_FOR_SESSION
        gpu = object()
        cpu = object()
        try:
            generate.PIPELINES = {
                ('balanced', 'cuda'): (gpu, 'CUDA'),
                ('balanced', 'cpu'): (cpu, 'CPU'),
            }
            generate.ACTIVE_LORA = {id(gpu): 'gpu_lora', id(cpu): 'cpu_lora'}
            generate.GPU_DISABLED_FOR_SESSION = False
            self.assertEqual(generate.disable_gpu_after_failure(), 1)
            self.assertTrue(generate.GPU_DISABLED_FOR_SESSION)
            self.assertNotIn(('balanced', 'cuda'), generate.PIPELINES)
            self.assertIs(generate.PIPELINES[('balanced', 'cpu')][0], cpu)
            self.assertNotIn(id(gpu), generate.ACTIVE_LORA)
            self.assertEqual(generate.ACTIVE_LORA[id(cpu)], 'cpu_lora')
            self.assertEqual(generate.disable_gpu_after_failure(), 0)
        finally:
            generate.PIPELINES = old_pipelines
            generate.ACTIVE_LORA = old_lora
            generate.GPU_DISABLED_FOR_SESSION = old_disabled


if __name__ == '__main__':
    unittest.main()
