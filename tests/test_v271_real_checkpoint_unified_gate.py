"""Ensure real training verification uses the same LoRA gate as inference."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from training.verify_real_checkpoint import verify_checkpoint


class RealCheckpointVerificationTests(unittest.TestCase):
    def test_shared_validator_is_required(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / 'real_lora'
            folder.mkdir()
            (folder / 'training_status.json').write_text(
                json.dumps({'status': 'SUCCEEDED', 'steps': 300,
                            'tensor_count': 2}), encoding='utf-8',
            )
            with patch(
                'training.verify_real_checkpoint.validate_adapter',
                return_value={'valid': False, 'reason': 'unpaired weights'},
            ):
                with self.assertRaisesRegex(ValueError, 'unpaired weights'):
                    verify_checkpoint(folder)
            with patch(
                'training.verify_real_checkpoint.validate_adapter',
                return_value={'valid': True, 'sha256': 'fixture-sha',
                              'tensor_count': 2},
            ):
                result = verify_checkpoint(folder)
            self.assertTrue(result['verified_checkpoint'])
            self.assertFalse(result['accuracy_evaluated'])

    def test_corrupt_or_nonobject_training_metadata_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            status = Path(temp) / 'training_status.json'
            for payload in ('[]', 'null', '"SUCCEEDED"', '{bad JSON'):
                status.write_text(payload, encoding='utf-8')
                with self.assertRaises(ValueError):
                    verify_checkpoint(Path(temp))

    def test_invalid_training_status_fails_before_checkpoint_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            status = folder / 'training_status.json'
            for record in (
                {'status': 'RUNNING', 'steps': 300, 'tensor_count': 2},
                {'status': 'SUCCEEDED', 'steps': 49, 'tensor_count': 2},
                {'status': 'SUCCEEDED', 'steps': True, 'tensor_count': 2},
                {'status': 'SUCCEEDED', 'steps': 300},
            ):
                status.write_text(json.dumps(record), encoding='utf-8')
                with self.assertRaises(ValueError):
                    verify_checkpoint(folder)


if __name__ == '__main__':
    unittest.main()
