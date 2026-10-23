"""Functional CUDA startup failure and sticky CPU fallback regression."""
import sys
import types
import unittest
from unittest.mock import patch

from app import generate


class FakePipeline:
    def __init__(self, *, fail_cuda=False):
        self.fail_cuda = fail_cuda
        self.location = None

    def to(self, device):
        if device == 'cuda' and self.fail_cuda:
            raise RuntimeError('CUDA initialization failed')
        self.location = device
        return self

    def enable_attention_slicing(self):
        return None

    def enable_vae_slicing(self):
        return None


class DeviceFallbackRuntimeTests(unittest.TestCase):
    def test_gpu_failure_disables_retry_and_keeps_cpu_cached(self):
        pipelines = []
        def from_pretrained(*_args, **kwargs):
            pipe = FakePipeline(fail_cuda=len(pipelines) == 0)
            pipelines.append((pipe, kwargs['torch_dtype']))
            return pipe

        fake_torch = types.ModuleType('torch')
        fake_torch.float16 = object()
        fake_torch.float32 = object()
        fake_torch.cuda = types.SimpleNamespace(is_available=lambda: True)
        fake_diffusers = types.ModuleType('diffusers')
        fake_diffusers.AutoPipelineForImage2Image = types.SimpleNamespace(
            from_pretrained=from_pretrained
        )
        previous_disabled = generate.GPU_DISABLED_FOR_SESSION
        previous_pipelines = generate.PIPELINES
        previous_lora = generate.ACTIVE_LORA
        try:
            generate.GPU_DISABLED_FOR_SESSION = False
            generate.PIPELINES = {}
            generate.ACTIVE_LORA = {}
            with patch.dict(sys.modules, {'torch': fake_torch, 'diffusers': fake_diffusers}):
                cpu_pipe, label = generate.get_pipeline('Cân bằng')
                self.assertIs(cpu_pipe, pipelines[1][0])
                self.assertEqual(pipelines[1][1], fake_torch.float32)
                self.assertEqual(cpu_pipe.location, 'cpu')
                self.assertIn('CPU dự phòng', label)
                self.assertTrue(generate.GPU_DISABLED_FOR_SESSION)
                cached_pipe, cached_label = generate.get_pipeline('Cân bằng')
                self.assertIs(cached_pipe, cpu_pipe)
                self.assertEqual(cached_label, label)
                self.assertEqual(len(pipelines), 2)
        finally:
            generate.GPU_DISABLED_FOR_SESSION = previous_disabled
            generate.PIPELINES = previous_pipelines
            generate.ACTIVE_LORA = previous_lora


if __name__ == '__main__':
    unittest.main()
