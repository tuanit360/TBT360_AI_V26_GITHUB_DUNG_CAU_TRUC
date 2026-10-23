"""Fail-closed inference tests; CI does not pretend to possess SD1.5 weights."""
import tempfile
import unittest
from pathlib import Path

from training.smoke_diffusers_inference import infer


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

    def test_reject_invalid_inference_arguments(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'image.png'
            with self.assertRaisesRegex(ValueError, 'steps'):
                infer(Path(temp) / 'adapter', 'sd15', path, steps=0)
            with self.assertRaisesRegex(ValueError, 'prompt'):
                infer(Path(temp) / 'adapter', 'sd15', path, prompt='   ')


if __name__ == '__main__':
    unittest.main()
