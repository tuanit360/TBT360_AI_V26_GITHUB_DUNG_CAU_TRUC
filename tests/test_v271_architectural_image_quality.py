"""Behavioral tests for architectural image export postprocessing."""
import unittest
from PIL import Image, ImageChops
from app.generate import postprocess_image, safe_prompt


class V271ArchitecturalImageQualityTests(unittest.TestCase):
    def test_lanczos_2x_preserves_source_and_dimensions(self):
        source = Image.new('RGB', (64, 48), (125, 135, 145))
        result = postprocess_image(source, 2, 0.0)
        self.assertEqual(result.size, (128, 96))
        self.assertEqual(source.size, (64, 48))
        self.assertEqual(result.getpixel((30, 30)), (125, 135, 145))

    def test_sharpening_does_not_create_halos_on_flat_surface(self):
        source = Image.new('RGB', (128, 128), (140, 145, 150))
        result = postprocess_image(source, 1, 1.0)
        self.assertIsNone(ImageChops.difference(source, result).getbbox())

    def test_prompt_emphasizes_consistent_facade_geometry(self):
        prompt = safe_prompt('office facade', next(iter(__import__(
            'app.generate', fromlist=['STYLE']).STYLE)))
        self.assertIn('consistent floor heights', prompt)
        self.assertIn('aligned facade grid', prompt)


if __name__ == '__main__':
    unittest.main()
