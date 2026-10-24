"""Fail-closed inference tests; CI does not pretend to possess SD1.5 weights."""
import tempfile
import unittest
from pathlib import Path

from training.smoke_diffusers_inference import infer, write_evidence


class InferenceSafetyTests(unittest.TestCase):
    def test_t600_refuses_low_free_ram_before_loading_model(self):
        import sys
        import types
        from unittest.mock import patch
        fake_torch = types.ModuleType('torch')
        fake_torch.cuda = types.SimpleNamespace(
            is_available=lambda: True,
            get_device_properties=lambda index: types.SimpleNamespace(
                total_memory=4 * 1024 ** 3,
            ),
            manual_seed=lambda seed: None,
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            adapter = root / 'adapter'
            adapter.mkdir()
            with patch(
                'app.lora_validation.validate_adapter',
                return_value={'valid': True, 'sha256': 'fake-test-hash'},
            ), patch.dict(sys.modules, {'torch': fake_torch}), patch(
                'training.local_hardware_diagnostic.available_memory_gib',
                return_value=4.3,
            ):
                with self.assertRaisesRegex(RuntimeError, 'system RAM available'):
                    infer(adapter, 'sd15', root / 'out.png', device='cuda')

    def test_seed_prompt_and_model_validate_before_pipeline(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for seed in (-1, True, 2 ** 63, '42', 4.5):
                with self.assertRaisesRegex(ValueError, 'seed'):
                    infer(folder / 'adapter', 'sd15', folder / 'output.png',
                          seed=seed)
            with self.assertRaisesRegex(ValueError, 'prompt'):
                infer(folder / 'adapter', 'sd15', folder / 'output.png',
                      prompt=None)
            with self.assertRaisesRegex(ValueError, 'base model'):
                infer(folder / 'adapter', 123, folder / 'output.png')

    def test_negative_prompt_and_cfg_reject_invalid_values(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for invalid in (float('nan'), float('inf'), -1, 21, True, '7.5'):
                with self.assertRaisesRegex(ValueError, 'guidance_scale'):
                    infer(
                        folder / 'adapter', 'sd15', folder / 'output.png',
                        guidance_scale=invalid,
                    )
            with self.assertRaisesRegex(ValueError, 'negative_prompt'):
                infer(
                    folder / 'adapter', 'sd15', folder / 'output.png',
                    negative_prompt=None,
                )

    def test_refuse_missing_model_before_loading_diffusers(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, 'base model'):
                infer(Path(temp) / 'adapter', '', Path(temp) / 'output.png')

    def test_lora_checkpoint_base_model_mismatch_fails_before_gpu_load(self):
        import json
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            adapter = folder / 'trained_adapter'
            adapter.mkdir()
            (adapter / 'training_status.json').write_text(
                json.dumps({'status': 'SUCCEEDED',
                            'base_model': 'stable-diffusion-v1-5/stable-diffusion-v1-5'}),
                encoding='utf-8',
            )
            output = folder / 'image.png'
            with patch(
                'app.lora_validation.validate_adapter',
                return_value={'valid': True, 'sha256': 'fixture-sha'},
            ):
                with self.assertRaisesRegex(ValueError, 'base model differs'):
                    infer(adapter, 'an-incompatible-base-model', output)
            self.assertFalse(output.exists())

    def test_refuse_existing_output_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'saved.png'
            output.write_bytes(b'important image')
            with self.assertRaises(FileExistsError):
                infer(Path(temp) / 'adapter', 'sd15', output)
            self.assertEqual(output.read_bytes(), b'important image')

    def test_partial_evidence_serialization_cleans_report(self):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / 'evidence.json'
            with self.assertRaises(TypeError):
                write_evidence(report, {'status': 'FAILED', 'bad': object()})
            self.assertFalse(report.exists())

    def test_exclusive_evidence_never_overwrites_existing_file(self):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / 'evidence.json'
            write_evidence(report, {'status': 'FAILED'})
            original = report.read_bytes()
            with self.assertRaises(FileExistsError):
                write_evidence(report, {'status': 'SUCCESS'})
            self.assertEqual(report.read_bytes(), original)

    def test_existing_report_is_never_overwritten_by_cli(self):
        import sys
        from unittest.mock import patch
        from training.smoke_diffusers_inference import main
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / 'evidence.json'
            report.write_text('previous verified evidence', encoding='utf-8')
            args = ['smoke', '--adapter', str(Path(temp) / 'adapter'),
                    '--model', 'sd15', '--image', str(Path(temp) / 'image.png'),
                    '--report', str(report)]
            with patch.object(sys, 'argv', args):
                with self.assertRaises(SystemExit) as error:
                    main()
            self.assertEqual(error.exception.code, 2)
            self.assertEqual(report.read_text(encoding='utf-8'),
                             'previous verified evidence')

    def test_corrupt_img2img_reference_fails_before_model_loading(self):
        with tempfile.TemporaryDirectory() as temp:
            reference = Path(temp) / 'corrupt.png'
            reference.write_bytes(b'not a decodable image')
            with self.assertRaises((OSError, ValueError)):
                infer(
                    Path(temp) / 'adapter', 'sd15',
                    Path(temp) / 'output.png', reference=reference,
                )
            self.assertFalse((Path(temp) / 'output.png').exists())

    def test_missing_img2img_reference_fails_before_loading_model(self):
        with tempfile.TemporaryDirectory() as temp:
            reference = Path(temp) / 'missing.png'
            with self.assertRaises(FileNotFoundError):
                infer(
                    Path(temp) / 'adapter', 'sd15',
                    Path(temp) / 'out.png', reference=reference,
                )

    def test_tiny_img2img_reference_is_rejected(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as temp:
            reference = Path(temp) / 'tiny.png'
            Image.new('RGB', (32, 32), 'white').save(reference)
            with self.assertRaisesRegex(ValueError, 'too small'):
                infer(
                    Path(temp) / 'adapter', 'sd15',
                    Path(temp) / 'out.png', reference=reference,
                )

    def test_img2img_zero_effective_denoising_steps_are_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, 'at least one denoising step'):
                infer(
                    Path(temp) / 'adapter', 'sd15',
                    Path(temp) / 'image.png',
                    reference=Path(temp) / 'reference.png',
                    steps=1, strength=0.4,
                )
            with self.assertRaisesRegex(ValueError, 'at least one denoising step'):
                infer(
                    Path(temp) / 'adapter', 'sd15',
                    Path(temp) / 'image.png',
                    reference=Path(temp) / 'reference.png',
                    steps=15, strength=0.05,
                )

    def test_invalid_direct_call_parameters_fail_before_inference(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            for bad in (float('nan'), float('inf'), True, '0.5'):
                with self.assertRaises(ValueError):
                    infer(
                        folder / 'adapter', 'sd15', folder / 'out.png',
                        reference=folder / 'reference.png', strength=bad,
                    )
            for bad_steps in (True, 1.5, '15', 0, 101):
                with self.assertRaises(ValueError):
                    infer(
                        folder / 'adapter', 'sd15', folder / 'out.png',
                        steps=bad_steps,
                    )

    def test_invalid_img2img_strength_fails_before_model_load(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, 'strength'):
                infer(
                    Path(temp) / 'adapter', 'sd15',
                    Path(temp) / 'out.png',
                    reference=Path(temp) / 'reference.png',
                    strength=0,
                )

    def test_reject_invalid_inference_arguments(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'image.png'
            with self.assertRaisesRegex(ValueError, 'steps'):
                infer(Path(temp) / 'adapter', 'sd15', path, steps=0)
            with self.assertRaisesRegex(ValueError, 'prompt'):
                infer(Path(temp) / 'adapter', 'sd15', path, prompt='   ')


if __name__ == '__main__':
    unittest.main()
