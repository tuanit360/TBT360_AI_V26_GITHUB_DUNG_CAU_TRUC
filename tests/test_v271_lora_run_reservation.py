"""Run reservation regression without CUDA or model checkpoints."""
import tempfile
import unittest
from pathlib import Path

from training.run_lora import reserve_run_directory


class LoRARunReservationTests(unittest.TestCase):
    def test_unique_run_directory_is_reserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reserved = reserve_run_directory(root, 'Office_LoRA_V1')
            self.assertTrue(reserved.is_dir())
            (reserved / 'training_status.json').write_text(
                '{"status": "FAILED"}', encoding='utf-8'
            )
            with self.assertRaises(FileExistsError):
                reserve_run_directory(root, 'Office_LoRA_V1')
            self.assertIn(
                'FAILED',
                (reserved / 'training_status.json').read_text(encoding='utf-8'),
            )

    def test_invalid_names_never_escape_run_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('../outside', '', 'bad name', 'a/b'):
                with self.subTest(name=name):
                    with self.assertRaises(ValueError):
                        reserve_run_directory(root, name)
            self.assertFalse((root / 'loras').exists())


if __name__ == '__main__':
    unittest.main()
