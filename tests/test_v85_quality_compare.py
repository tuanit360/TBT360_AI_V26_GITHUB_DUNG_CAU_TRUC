import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from app.architecture_quality_compare import compare_images, export_comparison


class V85ComparisonTests(unittest.TestCase):
    def test_identical_images_are_zero_difference(self):
        image = Image.new('RGB', (200, 180), '#abcdef')
        composite, result = compare_images(image, image, seed=123)
        self.assertEqual(composite.size, (400, 180))
        self.assertEqual(result['mean_pixel_difference_0_255'], 0)
        self.assertFalse(result['same_seed_generation_verified'])

    def test_different_images_and_export(self):
        first = Image.new('RGB', (200, 180), 'black')
        second = Image.new('RGB', (200, 180), 'white')
        with tempfile.TemporaryDirectory() as tmp:
            _, report = export_comparison(first, second, tmp, seed=8)
            self.assertGreater(report['mean_pixel_difference_0_255'], 200)
            self.assertEqual(len(report['files_sha256']), 3)
            self.assertEqual(json.loads((Path(tmp)/'comparison.json').read_text())['seed_user_supplied'], 8)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            compare_images(None, Image.new('RGB', (200, 180)))
