import json
import tempfile
import unittest
from pathlib import Path

from app.cpu_readiness import inspect_local_assets


class V271ModelIntegrityTests(unittest.TestCase):
    def test_index_alone_is_not_a_ready_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / 'models' / 'sd15'
            model.mkdir(parents=True)
            (model / 'model_index.json').write_text(
                json.dumps({'_class_name': 'StableDiffusionPipeline'}),
                encoding='utf-8',
            )
            info = inspect_local_assets(directory)
            self.assertTrue(info['model_valid_index'])
            self.assertFalse(info['model_files_complete'])
            self.assertIn('unet', info['missing_components'])

    def test_components_and_weights_are_required(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / 'models' / 'sd15'
            model.mkdir(parents=True)
            (model / 'model_index.json').write_text(
                json.dumps({'_class_name': 'StableDiffusionPipeline'}),
                encoding='utf-8',
            )
            for component in ('unet', 'vae', 'text_encoder', 'tokenizer', 'scheduler'):
                part = model / component
                part.mkdir()
                if component in ('unet', 'vae', 'text_encoder'):
                    (part / 'diffusion_pytorch_model.safetensors').write_bytes(b'test')
            info = inspect_local_assets(directory)
            self.assertTrue(info['model_files_complete'])
            self.assertEqual(info['missing_components'], [])
            self.assertFalse(info['generation_verified'])


if __name__ == '__main__':
    unittest.main()
