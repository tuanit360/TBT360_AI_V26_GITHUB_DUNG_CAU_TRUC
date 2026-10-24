"""Real checkpoint selection contract without fabricated training claims."""
import tempfile
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from training.select_local_lora import newest_verified_adapter


class LocalLoRASelectionTests(unittest.TestCase):
    def test_missing_or_invalid_checkpoint_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, 'No verified'):
                newest_verified_adapter(root)
            (root / 'invalid_lora').mkdir()
            with self.assertRaisesRegex(ValueError, 'No verified'):
                newest_verified_adapter(root)

    def test_newest_valid_checkpoint_selected_not_latest_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / 'lora_a'
            recent = root / 'lora_b'
            invalid = root / 'lora_z'
            for folder in (old, recent, invalid):
                folder.mkdir()
            os.utime(old, ns=(1000000000, 1000000000))
            os.utime(recent, ns=(2000000000, 2000000000))
            os.utime(invalid, ns=(3000000000, 3000000000))
            def fake_validate(folder):
                return {'valid': folder.name != 'lora_z'}
            with patch('training.select_local_lora.validate_adapter',
                       side_effect=fake_validate):
                self.assertEqual(newest_verified_adapter(root), 'lora_b')

    def test_windows_launcher_uses_verified_selection(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / 'RUN_T600_INFERENCE_ONLY_WINDOWS.bat').read_text('utf-8')
        self.assertIn('training.select_local_lora', script)
        self.assertNotIn('set "ADAPTER_NAME=t600_local_trial"', script)
        self.assertIn('training.verify_real_checkpoint', script)


if __name__ == '__main__':
    unittest.main()
