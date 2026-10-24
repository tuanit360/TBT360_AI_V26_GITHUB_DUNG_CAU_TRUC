import unittest
from PIL import Image
from app.architecture_vlm import infer_architecture, PROMPT


class V146VisionTests(unittest.TestCase):
    def test_missing_checkpoint_fails_closed(self):
        with self.assertRaises(ValueError):
            infer_architecture(Image.new('RGB', (512, 384)), '/no/local/vlm/checkpoint', 'office_146')

    def test_prompt_explicitly_blocks_fabricated_bim(self):
        self.assertIn('Do not invent room plans', PROMPT)
        self.assertIn('IFC', PROMPT)
