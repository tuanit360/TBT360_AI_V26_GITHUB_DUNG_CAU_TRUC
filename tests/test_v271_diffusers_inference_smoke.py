"""Fail-closed inference tests; CI does not pretend to possess SD1.5 weights."""
import tempfile
import unittest
from pathlib import Path

from training.smoke_diffusers_inference import infer, write_evidence


class InferenceSafetyTests(unittest.TestCase):
    def test_refuse_missing_model_before_loading_diffusers(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, 'base model'):
                infer(Path(temp) / 'adapter', '', Path(temp) / 'output.png')

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
