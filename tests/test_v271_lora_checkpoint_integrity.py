"""Real safetensors validation: matching SHA256 alone is insufficient."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from app.lora_validation import validate_adapter


class V271AdapterIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name) / 'architecture_adapter'
        self.folder.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def write_status(self, data, tensor_count=1):
        weights = self.folder / 'pytorch_lora_weights.safetensors'
        weights.write_bytes(data)
        (self.folder / 'training_status.json').write_text(
            json.dumps({
                'status': 'SUCCEEDED',
                'weights_bytes': len(data),
                'weights_sha256': hashlib.sha256(data).hexdigest(),
                'tensor_count': tensor_count,
            }), encoding='utf-8',
        )

    def test_arbitrary_bytes_with_matching_digest_are_rejected(self):
        self.write_status(b'not a safetensors LoRA')
        self.assertFalse(validate_adapter(self.folder)['valid'])

    def test_empty_tensor_file_rejected(self):
        from safetensors.torch import save
        self.write_status(save({}), tensor_count=0)
        self.assertFalse(validate_adapter(self.folder)['valid'])

    def test_unpaired_lora_factor_is_rejected(self):
        import torch
        from safetensors.torch import save
        self.write_status(save({'x.lora_down.weight': torch.ones((2, 2))}))
        self.assertFalse(validate_adapter(self.folder)['valid'])

    def test_mismatched_lora_ranks_are_rejected(self):
        import torch
        from safetensors.torch import save
        data = save({
            'module.lora_down.weight': torch.ones((3, 8)),
            'module.lora_up.weight': torch.ones((12, 2)),
        })
        self.write_status(data, tensor_count=2)
        result = validate_adapter(self.folder)
        self.assertFalse(result['valid'])
        self.assertIn('shapes', result['reason'])

    def test_matching_nonsquare_lora_factors_accepted(self):
        import torch
        from safetensors.torch import save
        data = save({
            'module.lora_down.weight': torch.ones((3, 8)),
            'module.lora_up.weight': torch.ones((12, 3)),
        })
        self.write_status(data, tensor_count=2)
        self.assertTrue(validate_adapter(self.folder)['valid'])

    def test_real_tensor_file_and_count_verified(self):
        import torch
        from safetensors.torch import save
        data = save({'lora_unet_test.lora_down.weight': torch.ones((2, 2)), 'lora_unet_test.lora_up.weight': torch.ones((2, 2))})
        self.write_status(data, tensor_count=2)
        self.assertTrue(validate_adapter(self.folder)['valid'])
        self.write_status(data, tensor_count=3)
        self.assertFalse(validate_adapter(self.folder)['valid'])


if __name__ == '__main__':
    unittest.main()
