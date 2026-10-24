import unittest
from app.inference_memory_policy import (
    choose_device_mode, configure_pipeline_device,
)


class DummyCuda:
    def __init__(self, gib):
        self.gib = gib

    def get_device_properties(self, index):
        class Props:
            pass
        result = Props()
        result.total_memory = int(self.gib * (1024 ** 3))
        return result


class DummyTorch:
    def __init__(self, gib):
        self.cuda = DummyCuda(gib)


class DummyPipeline:
    def __init__(self):
        self.mode = None

    def to(self, device):
        self.mode = device

    def enable_sequential_cpu_offload(self):
        self.mode = 'offloaded'


class MemoryPolicyTests(unittest.TestCase):
    def test_low_vram_chooses_offload(self):
        self.assertEqual(choose_device_mode('cuda', '', 4), 'sequential_offload')
        self.assertEqual(choose_device_mode('cuda', '', 8), 'cuda')
        self.assertEqual(choose_device_mode('cpu', '', None), 'cpu')

    def test_configures_low_vram_without_gpu_upload(self):
        pipe = DummyPipeline()
        self.assertEqual(
            configure_pipeline_device(pipe, DummyTorch(4), 'cuda', ''),
            'sequential_offload',
        )
        self.assertEqual(pipe.mode, 'offloaded')

    def test_configures_cpu_without_cuda(self):
        pipe = DummyPipeline()
        configure_pipeline_device(pipe, DummyTorch(4), 'cpu', '')
        self.assertEqual(pipe.mode, 'cpu')


if __name__ == '__main__':
    unittest.main()
