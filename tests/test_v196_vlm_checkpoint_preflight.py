import json
import tempfile
import unittest
from pathlib import Path

from app.vlm_checkpoint_preflight import inspect_local_vlm_checkpoint


class V196VLMPreflightTests(unittest.TestCase):
    def test_rejects_fake_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / 'config.json').write_text(json.dumps({'model_type': 'llava'}))
            with self.assertRaises(ValueError):
                inspect_local_vlm_checkpoint(folder)
            (folder / 'processor_config.json').write_text('{}')
            with self.assertRaises(ValueError):
                inspect_local_vlm_checkpoint(folder)

    def test_accepts_local_weights_but_never_claims_training(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / 'config.json').write_text(json.dumps({'model_type': 'llava'}))
            (folder / 'preprocessor_config.json').write_text('{}')
            (folder / 'model.safetensors').write_bytes(b'a' * 2048)
            status = inspect_local_vlm_checkpoint(folder)
            self.assertTrue(status['checkpoint_files_present'])
            self.assertFalse(status['model_loaded'])
            self.assertFalse(status['gpu_inference_verified'])
            self.assertFalse(status['image_to_bim_trained'])

    def test_rejects_shard_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / 'config.json').write_text(json.dumps({'model_type': 'llava'}))
            (folder / 'preprocessor_config.json').write_text('{}')
            (folder / 'model.safetensors.index.json').write_text(
                json.dumps({'weight_map': {'layer0':'../outside.safetensors'}}))
            with self.assertRaises(ValueError):
                inspect_local_vlm_checkpoint(folder)
