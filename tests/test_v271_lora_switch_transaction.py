"""LoRA switches must preserve the previous pipeline until validation passes."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import generate


class FakeAdapterPipeline:
    def __init__(self, fail_load=False):
        self.fail_load = fail_load
        self.events = []

    def unload_lora_weights(self):
        self.events.append('unload')

    def load_lora_weights(self, *_args, **_kwargs):
        self.events.append('load')
        if self.fail_load:
            raise RuntimeError('corrupt tensor')


class LoRASwitchLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.old_cache = generate.PIPELINES
        self.old_active = generate.ACTIVE_LORA
        generate.PIPELINES = {}
        generate.ACTIVE_LORA = {}

    def tearDown(self):
        generate.PIPELINES = self.old_cache
        generate.ACTIVE_LORA = self.old_active

    def test_invalid_adapter_does_not_unload_old_lora(self):
        pipe = FakeAdapterPipeline()
        generate.PIPELINES[('low', 'cpu')] = (pipe, 'CPU')
        generate.ACTIVE_LORA[id(pipe)] = 'old'
        with patch.object(generate, 'installed_loras', return_value=['Không dùng LoRA']):
            with self.assertRaisesRegex(ValueError, 'hash'):
                generate.select_lora(pipe, 'low', 'invalid')
        self.assertEqual(pipe.events, [])
        self.assertEqual(generate.ACTIVE_LORA[id(pipe)], 'old')
        self.assertIn(('low', 'cpu'), generate.PIPELINES)

    def test_failed_load_evicts_only_corrupted_pipeline(self):
        pipe = FakeAdapterPipeline(fail_load=True)
        good = FakeAdapterPipeline()
        generate.PIPELINES[('low', 'cuda')] = (pipe, 'CUDA')
        generate.PIPELINES[('low', 'cpu')] = (good, 'CPU')
        generate.ACTIVE_LORA[id(pipe)] = 'old'
        generate.ACTIVE_LORA[id(good)] = 'other'
        with tempfile.TemporaryDirectory() as temp:
            adapter = Path(temp) / 'candidate'
            adapter.mkdir()
            (adapter / 'pytorch_lora_weights.safetensors').write_bytes(b'test')
            with patch.object(generate, 'LORA_DIR', Path(temp)), patch.object(
                generate, 'installed_loras',
                return_value=['Không dùng LoRA', 'candidate'],
            ):
                with self.assertRaisesRegex(RuntimeError, 'corrupt tensor'):
                    generate.select_lora(pipe, 'low', 'candidate')
        self.assertEqual(pipe.events, ['unload', 'load'])
        self.assertNotIn(('low', 'cuda'), generate.PIPELINES)
        self.assertNotIn(id(pipe), generate.ACTIVE_LORA)
        self.assertIs(generate.PIPELINES[('low', 'cpu')][0], good)
        self.assertEqual(generate.ACTIVE_LORA[id(good)], 'other')


if __name__ == '__main__':
    unittest.main()
