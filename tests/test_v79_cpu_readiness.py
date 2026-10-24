import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from app.cpu_readiness import inspect_local_assets


class V79ReadinessTests(unittest.TestCase):
    def test_missing_model_and_cpu_are_not_claimed_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = inspect_local_assets(tmp)
            self.assertFalse(report['model_found'])
            self.assertFalse(report['generation_verified'])
            self.assertEqual(report['recommended_count'], 1)
            self.assertEqual(report['recommended_steps'], 15)
            self.assertTrue(any('CPU-only' in item for item in report['issues']))

    def test_valid_model_index_and_verified_lora(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model = root / 'models' / 'sd15'
            model.mkdir(parents=True)
            (model / 'model_index.json').write_text(json.dumps({'_class_name': 'StableDiffusionPipeline'}))
            lora = root / 'loras' / 'demo'
            lora.mkdir(parents=True)
            weights = b'synthetic fixture; not a usable model'
            (lora / 'pytorch_lora_weights.safetensors').write_bytes(weights)
            (lora / 'training_status.json').write_text(json.dumps({
                'status': 'SUCCEEDED',
                'weights_bytes': len(weights),
                'weights_sha256': hashlib.sha256(weights).hexdigest(),
            }))
            report = inspect_local_assets(root, cuda_available=True)
            self.assertTrue(report['model_valid_index'])
            self.assertEqual(report['lora_verified_count'], 1)
            self.assertFalse(report['generation_verified'])

    def test_corrupt_metadata_not_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model = root / 'models' / 'sd15'
            model.mkdir(parents=True)
            (model / 'model_index.json').write_text('not json')
            report = inspect_local_assets(root)
            self.assertFalse(report['model_valid_index'])
            self.assertTrue(report['issues'])
