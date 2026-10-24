"""GPU-memory mode selection regression without fetching or faking model weights."""
import types
import unittest
from unittest.mock import Mock

from training.smoke_diffusers_inference import configure_pipeline_memory


class LowVRAMPipelineTests(unittest.TestCase):
    def gpu(self, vram):
        return types.SimpleNamespace(
            cuda=types.SimpleNamespace(
                get_device_properties=lambda index: types.SimpleNamespace(
                    total_memory=int(vram * 1024 ** 3)
                )
            )
        )

    def test_t600_class_4gib_uses_offload_without_cuda_to(self):
        pipeline = Mock()
        profile = configure_pipeline_memory(pipeline, 'cuda', self.gpu(4))
        self.assertEqual(profile, 'cuda_model_cpu_offload')
        pipeline.enable_model_cpu_offload.assert_called_once_with()
        pipeline.to.assert_not_called()

    def test_gpu_8gib_keeps_standard_cuda(self):
        pipeline = Mock()
        profile = configure_pipeline_memory(pipeline, 'cuda', self.gpu(8))
        self.assertEqual(profile, 'cuda_fp16')
        pipeline.to.assert_called_once_with('cuda')
        pipeline.enable_model_cpu_offload.assert_not_called()

    def test_insufficient_vram_fails_closed(self):
        pipeline = Mock()
        with self.assertRaisesRegex(RuntimeError, 'below 3.5 GiB'):
            configure_pipeline_memory(pipeline, 'cuda', self.gpu(2))
        pipeline.to.assert_not_called()

    def test_cpu_stays_on_cpu(self):
        pipeline = Mock()
        self.assertEqual(
            configure_pipeline_memory(pipeline, 'cpu', self.gpu(2)), 'cpu',
        )
        pipeline.to.assert_called_once_with('cpu')


if __name__ == '__main__':
    unittest.main()
