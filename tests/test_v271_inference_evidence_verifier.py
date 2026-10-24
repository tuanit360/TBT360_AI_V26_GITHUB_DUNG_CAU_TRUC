"""Artifact verifier regressions: independently check actual saved PNG bytes."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from app.generated_image_gate import validate_generated_image
from training.verify_inference_evidence import verify_inference_evidence


class V271EvidenceVerificationTests(unittest.TestCase):
    def test_valid_artifacts_are_integrity_checked_not_model_certified(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            image_path = folder / 'image.png'
            report_path = folder / 'evidence.json'
            image = Image.new('RGB', (512, 512))
            image.putdata([
                ((x * 3) % 256, (y * 5) % 256, (x + y) % 256)
                for y in range(512) for x in range(512)
            ])
            image.save(image_path)
            digest = hashlib.sha256(image_path.read_bytes()).hexdigest()
            record = {
                'status': 'DIFFUSERS_INFERENCE_EXECUTED_NOT_QUALITY_VERIFIED',
                'image': str(image_path),
                'image_sha256': digest,
                'adapter_sha256': 'example-adapter-hash',
                'quality_evaluated': False,
                'prompt': 'Architectural facade',
                'negative_prompt': 'warped windows',
                'guidance_scale': 7.5,
                'device': 'cpu',
                'generation_seconds': 1.25,
                'cuda_peak_allocated_mib': None,
                'seed': 42,
                'steps': 15,
                'generation_mode': 'text2img',
                'basic_image_gate': validate_generated_image(
                    image, expected_size=(512, 512)
                ),
            }
            report_path.write_text(json.dumps(record), encoding='utf-8')
            result = verify_inference_evidence(report_path, image_path)
            self.assertEqual(
                result['status'], 'ARTIFACT_INTEGRITY_PASS_NOT_MODEL_PROVEN'
            )
            self.assertFalse(result['real_model_execution_proven_by_artifacts_alone'])
            for field, invalid in (
                ('prompt', ''),
                ('negative_prompt', None),
                ('guidance_scale', float('nan')),
                ('guidance_scale', 21),
                ('seed', True),
                ('steps', 0),
            ):
                changed = dict(record, **{field: invalid})
                report_path.write_text(
                    json.dumps(changed), encoding='utf-8',
                )
                self.assertEqual(
                    verify_inference_evidence(report_path, image_path)['status'],
                    'BLOCKED',
                    field,
                )
            report_path.write_text(json.dumps(record), encoding='utf-8')
            image_path.write_bytes(b'corrupted')
            self.assertEqual(
                verify_inference_evidence(report_path, image_path)['status'],
                'BLOCKED',
            )
            image.save(image_path)
            record['basic_image_gate']['mean_brightness'] = -1
            report_path.write_text(json.dumps(record), encoding='utf-8')
            self.assertEqual(
                verify_inference_evidence(report_path, image_path)['status'],
                'BLOCKED',
            )

    def test_jpeg_renamed_png_is_blocked_even_with_matching_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            image_path = folder / 'fake.png'
            report_path = folder / 'evidence.json'
            image = Image.new('RGB', (512, 512))
            image.putdata([
                ((x * 3) % 256, (y * 5) % 256, (x + y) % 256)
                for y in range(512) for x in range(512)
            ])
            image.save(image_path, format='JPEG')
            with Image.open(image_path) as decoded:
                metrics = validate_generated_image(
                    decoded, expected_size=(512, 512)
                )
            record = {
                'status': 'DIFFUSERS_INFERENCE_EXECUTED_NOT_QUALITY_VERIFIED',
                'image': str(image_path),
                'image_sha256': hashlib.sha256(image_path.read_bytes()).hexdigest(),
                'adapter_sha256': 'example-adapter-hash',
                'quality_evaluated': False,
                'basic_image_gate': metrics,
            }
            report_path.write_text(json.dumps(record), encoding='utf-8')
            result = verify_inference_evidence(report_path, image_path)
            self.assertEqual(result['status'], 'BLOCKED')
            self.assertIn('PNG', result['reason'])

    def test_changed_img2img_source_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = folder / 'reference.png'
            Image.new('RGB', (256, 256), 'white').save(source)
            image_path = folder / 'image.png'
            report_path = folder / 'report.json'
            image = Image.new('RGB', (512, 512))
            image.putdata([
                ((x * 3) % 256, (y * 5) % 256, (x + y) % 256)
                for y in range(512) for x in range(512)
            ])
            image.save(image_path)
            record = {
                'status': 'DIFFUSERS_INFERENCE_EXECUTED_NOT_QUALITY_VERIFIED',
                'generation_mode': 'img2img',
                'steps': 4,
                'strength': 0.5,
                'reference_image': str(source),
                'reference_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'reference_geometry_verified': False,
                'image': str(image_path),
                'image_sha256': hashlib.sha256(image_path.read_bytes()).hexdigest(),
                'adapter_sha256': 'test-only-checksum',
                'quality_evaluated': False,
                'prompt': 'Architectural facade',
                'negative_prompt': 'warped windows',
                'guidance_scale': 7.5,
                'seed': 42,
                'basic_image_gate': validate_generated_image(image, expected_size=(512, 512)),
            }
            report_path.write_text(json.dumps(record), encoding='utf-8')
            self.assertEqual(
                verify_inference_evidence(report_path, image_path)['status'],
                'ARTIFACT_INTEGRITY_PASS_NOT_MODEL_PROVEN',
            )
            record['strength'] = 0.1
            report_path.write_text(json.dumps(record), encoding='utf-8')
            self.assertEqual(
                verify_inference_evidence(report_path, image_path)['status'],
                'BLOCKED',
            )
            for invalid_strength in (True, float('nan'), float('inf'), -1, '0.5'):
                record['strength'] = invalid_strength
                report_path.write_text(json.dumps(record), encoding='utf-8')
                self.assertEqual(
                    verify_inference_evidence(report_path, image_path)['status'],
                    'BLOCKED',
                )
            record['strength'] = 0.5
            for invalid_steps in (True, 0, 101, 4.5, '4'):
                record['steps'] = invalid_steps
                report_path.write_text(json.dumps(record), encoding='utf-8')
                self.assertEqual(
                    verify_inference_evidence(report_path, image_path)['status'],
                    'BLOCKED',
                )
            record['steps'] = 4
            record['strength'] = 0.5
            report_path.write_text(json.dumps(record), encoding='utf-8')
            # Even a matching SHA is not enough if the image cannot decode.
            source.write_bytes(b'corrupted but checksummed reference')
            record['reference_sha256'] = hashlib.sha256(
                source.read_bytes()
            ).hexdigest()
            report_path.write_text(json.dumps(record), encoding='utf-8')
            self.assertEqual(
                verify_inference_evidence(report_path, image_path)['status'],
                'BLOCKED',
            )
            source.write_bytes(b'modified reference')
            self.assertEqual(
                verify_inference_evidence(report_path, image_path)['status'],
                'BLOCKED',
            )

    def test_failed_report_cannot_pass_integrity_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            report_path = folder / 'report.json'
            report_path.write_text('{"status": "FAILED"}', encoding='utf-8')
            self.assertEqual(
                verify_inference_evidence(report_path, folder / 'missing.png')['status'],
                'BLOCKED',
            )


if __name__ == '__main__':
    unittest.main()
