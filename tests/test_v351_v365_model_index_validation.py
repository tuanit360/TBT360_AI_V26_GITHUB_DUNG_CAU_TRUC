import json
import tempfile
import unittest
from pathlib import Path
from app.model_index_validation import validate_sd15_index


class ModelIndexTests(unittest.TestCase):
    def test_invalid_index_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'model_index.json'
            path.write_text('{}', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'missing components'):
                validate_sd15_index(root)
            path.write_text('{broken', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'invalid'):
                validate_sd15_index(root)

    def test_complete_declared_components(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'model_index.json'
            path.write_text(json.dumps({
                key: ['diffusers', key] for key in
                ('unet', 'vae', 'scheduler', 'text_encoder', 'tokenizer')
            }), encoding='utf-8')
            self.assertTrue(validate_sd15_index(root))


if __name__ == '__main__':
    unittest.main()
