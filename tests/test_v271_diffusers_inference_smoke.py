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

    def test_reject_invalid_inference_arguments(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'image.png'
            with self.assertRaisesRegex(ValueError, 'steps'):
                infer(Path(temp) / 'adapter', 'sd15', path, steps=0)
            with self.assertRaisesRegex(ValueError, 'prompt'):
                infer(Path(temp) / 'adapter', 'sd15', path, prompt='   ')


if __name__ == '__main__':
    unittest.main()
