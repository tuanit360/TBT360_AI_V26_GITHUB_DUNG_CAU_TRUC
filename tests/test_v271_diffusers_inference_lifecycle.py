"""Inference lifecycle tests use a fake pipeline, never claim real SD1.5 inference."""
import hashlib
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from training.smoke_diffusers_inference import infer


class StubPipeline:
    def __init__(self, image):
        self.image = image
        self.loaded = False

    def to(self, device):
        return self

    def load_lora_weights(self, path, weight_name):
        self.loaded = True

    def __call__(self, **kwargs):
        if not self.loaded:
            raise RuntimeError('LoRA not loaded')
        return types.SimpleNamespace(images=[self.image])


class InferenceLifecycleTests(unittest.TestCase):
    def invoke(self, folder, image):
        adapter = folder / 'adapter'
        output = folder / 'result.png'
        pipeline = StubPipeline(image)
        stub = types.ModuleType('diffusers')
        stub.StableDiffusionPipeline = types.SimpleNamespace(
            from_pretrained=lambda *args, **kwargs: pipeline
        )
        with patch.dict(sys.modules, {'diffusers': stub}):
            with patch(
                'app.lora_validation.validate_adapter',
                return_value={'valid': True, 'sha256': 'fixture-hash'},
            ):
                result = infer(adapter, 'mock-model-not-real', output, steps=1)
        return result, output

    def test_writes_decodable_png_with_hash_and_explicit_mock_result(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            image = Image.new('RGB', (512, 512))
            image.putdata([
                ((x * 3) % 256, (y * 5) % 256, (x + y) % 256)
                for y in range(512) for x in range(512)
            ])
            result, output = self.invoke(folder, image)
            self.assertEqual(
                result['status'],
                'DIFFUSERS_INFERENCE_EXECUTED_NOT_QUALITY_VERIFIED',
            )
            self.assertFalse(result['quality_evaluated'])
            with Image.open(output) as saved:
                self.assertEqual(saved.size, (512, 512))
                saved.verify()
            self.assertEqual(
                hashlib.sha256(output.read_bytes()).hexdigest(),
                result['image_sha256'],
            )

    def test_blank_output_rejected_without_writing_a_file(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            with self.assertRaisesRegex(ValueError, 'black|blank'):
                self.invoke(folder, Image.new('RGB', (512, 512), 'black'))
            self.assertFalse((folder / 'result.png').exists())

    def test_incorrect_dimensions_rejected_without_writing_a_file(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            with self.assertRaisesRegex(ValueError, 'size'):
                self.invoke(folder, Image.new('RGB', (256, 512), 'white'))
            self.assertFalse((folder / 'result.png').exists())


if __name__ == '__main__':
    unittest.main()
