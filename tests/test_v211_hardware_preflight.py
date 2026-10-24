import unittest
from training.hardware_preflight import summarize_hardware


class V211HardwareTests(unittest.TestCase):
    def test_unknown_gpu_blocks_train_but_not_cpu_portable(self):
        result = summarize_hardware(False)
        self.assertFalse(result['gpu_training_ready'])
        self.assertTrue(result['windows_portable_cpu_available'])

    def test_small_cuda_gpu_requires_remote_training(self):
        result = summarize_hardware(True, 4, 'NVIDIA T600 Laptop')
        self.assertFalse(result['gpu_training_ready'])
        self.assertEqual(result['sd15_lora_8g_preflight'], 'blocked')

    def test_sufficient_vram_is_preflight_not_training_result(self):
        result = summarize_hardware(True, 12, 'GPU')
        self.assertTrue(result['gpu_training_ready'])
        self.assertEqual(result['architecture_vlm_finetuning'], 'not_verified')
