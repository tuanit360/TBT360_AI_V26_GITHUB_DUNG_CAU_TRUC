"""Safety gates of the real Diffusers load smoke (no model download in CI)."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from training.smoke_diffusers_lora import smoke_load


class DiffusersLoadSmokeTests(unittest.TestCase):
    def test_invalid_adapter_rejected_before_any_model_loading(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / 'missing_weights'
            folder.mkdir()
            with patch('app.lora_validation.validate_adapter', return_value={
                'valid': False, 'reason': 'missing weights',
            }):
                with self.assertRaisesRegex(ValueError, 'structural gate'):
                    smoke_load(folder, 'not-a-real-model')

    def test_invalid_device_rejected_before_model_loading(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / 'named_adapter'
            folder.mkdir()
            with patch('training.smoke_diffusers_lora.validate_adapter',
                       return_value={'valid': True, 'sha256': 'test'}):
                with self.assertRaisesRegex(ValueError, 'device'):
                    smoke_load(folder, 'not-a-real-model', 'npu')


if __name__ == '__main__':
    unittest.main()
