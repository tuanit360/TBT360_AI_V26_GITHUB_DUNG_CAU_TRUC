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

    def test_exclusive_create_collision_does_not_delete_other_output(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            output = folder / 'result.png'
            image = Image.new('RGB', (512, 512))
            image.putdata([
                ((x * 3) % 256, (y * 5) % 256, (x + y) % 256)
                for y in range(512) for x in range(512)
            ])
            original_open = Path.open

            def collision(path, mode='r', *args, **kwargs):
                if Path(path) == output and mode == 'xb':
                    output.write_bytes(b'another process created this')
                    raise FileExistsError('concurrent output')
                return original_open(path, mode, *args, **kwargs)

            with patch.object(Path, 'open', collision):
                with self.assertRaises(FileExistsError):
                    self.invoke(folder, image)
            self.assertEqual(output.read_bytes(), b'another process created this')

    def test_partial_png_save_removes_only_own_incomplete_output(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            image = Image.new('RGB', (512, 512))
            image.putdata([
                ((x * 3) % 256, (y * 5) % 256, (x + y) % 256)
                for y in range(512) for x in range(512)
            ])
            def interrupted_save(image_object, stream, *args, **kwargs):
                stream.write(b'partial png')
                raise OSError('interrupted image encoding')
            with patch.object(Image.Image, 'save', interrupted_save):
                with self.assertRaisesRegex(OSError, 'interrupted'):
                    self.invoke(folder, image)
            self.assertFalse((folder / 'result.png').exists())

    def test_img2img_mock_pipeline_preserves_reference_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            reference = folder / 'reference.png'
            Image.new('RGB', (640, 480), 'white').save(reference)
            original_hash = hashlib.sha256(reference.read_bytes()).hexdigest()
            output = folder / 'output.png'
            image = Image.new('RGB', (512, 512))
            image.putdata([
                ((x * 3) % 256, (y * 5) % 256, (x + y) % 256)
                for y in range(512) for x in range(512)
            ])
            pipeline = StubPipeline(image)
            stub = types.ModuleType('diffusers')
            stub.StableDiffusionPipeline = types.SimpleNamespace(
                from_pretrained=lambda *args, **kwargs: self.fail(
                    'text2img pipeline must not be used for reference input'
                )
            )
            stub.StableDiffusionImg2ImgPipeline = types.SimpleNamespace(
                from_pretrained=lambda *args, **kwargs: pipeline
            )
            with patch.dict(sys.modules, {'diffusers': stub}):
                with patch(
                    'app.lora_validation.validate_adapter',
                    return_value={'valid': True, 'sha256': 'fixture-hash'},
                ):
                    result = infer(
                        folder / 'adapter', 'mock-model-not-real', output,
                        reference=reference, strength=0.5, steps=4,
                    )
            self.assertEqual(result['generation_mode'], 'img2img')
            self.assertEqual(result['reference_sha256'], original_hash)
            self.assertEqual(result['reference_image'], str(reference.resolve()))
            self.assertFalse(result['reference_geometry_verified'])
            self.assertEqual(result['strength'], 0.5)
            self.assertEqual(
                hashlib.sha256(output.read_bytes()).hexdigest(),
                result['image_sha256'],
            )
            self.assertEqual(hashlib.sha256(reference.read_bytes()).hexdigest(),
                             original_hash)

    def test_img2img_mock_output_passes_independent_evidence_audit(self):
        from training.smoke_diffusers_inference import write_evidence
        from training.verify_inference_evidence import verify_inference_evidence

        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            reference = folder / 'reference.png'
            Image.new('RGB', (640, 480), 'white').save(reference)
            output = folder / 'result.png'
            report = folder / 'evidence.json'
            image = Image.new('RGB', (512, 512))
            image.putdata([
                ((x * 3) % 256, (y * 5) % 256, (x + y) % 256)
                for y in range(512) for x in range(512)
            ])
            pipeline = StubPipeline(image)
            stub = types.ModuleType('diffusers')
            stub.StableDiffusionPipeline = types.SimpleNamespace(
                from_pretrained=lambda *args, **kwargs: self.fail(
                    'img2img must use its own pipeline'
                )
            )
            stub.StableDiffusionImg2ImgPipeline = types.SimpleNamespace(
                from_pretrained=lambda *args, **kwargs: pipeline
            )
            with patch.dict(sys.modules, {'diffusers': stub}):
                with patch(
                    'app.lora_validation.validate_adapter',
                    return_value={'valid': True, 'sha256': 'fixture-hash'},
                ):
                    result = infer(
                        folder / 'adapter', 'mock-model-not-real', output,
                        reference=reference, steps=4, strength=0.5,
                    )
            write_evidence(report, result)
            audit = verify_inference_evidence(report, output)
            self.assertEqual(
                audit['status'], 'ARTIFACT_INTEGRITY_PASS_NOT_MODEL_PROVEN'
            )
            self.assertFalse(audit['real_model_execution_proven_by_artifacts_alone'])
            reference.write_bytes(b'tampered-after-inference')
            self.assertEqual(
                verify_inference_evidence(report, output)['status'], 'BLOCKED',
            )

    def test_reference_modified_during_inference_blocks_output(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            reference = folder / 'reference.png'
            Image.new('RGB', (512, 512), 'white').save(reference)
            output = folder / 'output.png'
            image = Image.new('RGB', (512, 512))
            image.putdata([
                ((x * 3) % 256, (y * 5) % 256, (x + y) % 256)
                for y in range(512) for x in range(512)
            ])

            class ChangingPipeline(StubPipeline):
                def __call__(self, **kwargs):
                    reference.write_bytes(b'changed during generation')
                    return super().__call__(**kwargs)

            pipeline = ChangingPipeline(image)
            stub = types.ModuleType('diffusers')
            stub.StableDiffusionPipeline = types.SimpleNamespace(
                from_pretrained=lambda *args, **kwargs: pipeline
            )
            stub.StableDiffusionImg2ImgPipeline = types.SimpleNamespace(
                from_pretrained=lambda *args, **kwargs: pipeline
            )
            with patch.dict(sys.modules, {'diffusers': stub}):
                with patch(
                    'app.lora_validation.validate_adapter',
                    return_value={'valid': True, 'sha256': 'fixture-hash'},
                ):
                    with self.assertRaisesRegex(ValueError, 'during img2img inference'):
                        infer(
                            folder / 'adapter', 'mock-model-not-real',
                            output, steps=4, strength=0.5,
                            reference=reference,
                        )
            self.assertFalse(output.exists())

    def test_empty_diffusers_result_is_rejected_without_output(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            output = folder / 'result.png'
            class EmptyResultPipeline(StubPipeline):
                def __call__(self, **kwargs):
                    return types.SimpleNamespace(images=[])
            stub = types.ModuleType('diffusers')
            stub.StableDiffusionPipeline = types.SimpleNamespace(
                from_pretrained=lambda *args, **kwargs: EmptyResultPipeline(
                    Image.new('RGB', (512, 512))
                )
            )
            with patch.dict(sys.modules, {'diffusers': stub}):
                with patch(
                    'app.lora_validation.validate_adapter',
                    return_value={'valid': True, 'sha256': 'fixture-hash'},
                ):
                    with self.assertRaisesRegex(ValueError, 'no images'):
                        infer(folder / 'adapter', 'mock-model-not-real', output)
            self.assertFalse(output.exists())

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
