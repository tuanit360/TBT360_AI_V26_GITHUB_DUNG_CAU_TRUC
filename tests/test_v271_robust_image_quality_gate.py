"""Runtime quality-gate tests, including single-pixel blank image deception."""
import unittest
from PIL import Image, ImageDraw
from app.generated_image_gate import validate_generated_image


class V271ImageQualityGateTests(unittest.TestCase):
    def test_nearly_blank_with_one_bright_pixel_is_rejected(self):
        image = Image.new('RGB', (512, 512), (135, 135, 135))
        image.putpixel((0, 0), (255, 255, 255))
        with self.assertRaisesRegex(ValueError, 'visually blank'):
            validate_generated_image(image)

    def test_architectural_grayscale_edges_are_accepted(self):
        image = Image.new('RGB', (512, 512), (175, 175, 175))
        canvas = ImageDraw.Draw(image)
        canvas.rectangle((80, 80, 430, 420), fill=(95, 100, 105))
        canvas.rectangle((140, 140, 240, 320), fill=(40, 45, 50))
        evidence = validate_generated_image(image)
        self.assertGreaterEqual(evidence['robust_luminance_range'], 5)
        self.assertFalse(evidence['visual_design_verified'])

    def test_upscaled_output_wrong_size_is_rejected(self):
        generated = Image.new('RGB', (512, 512), (110, 120, 130))
        ImageDraw.Draw(generated).rectangle(
            (80, 80, 430, 430), fill=(190, 200, 210)
        )
        with self.assertRaisesRegex(ValueError, 'requested export dimensions'):
            validate_generated_image(generated, expected_size=(1024, 1024))

    def test_upscaled_output_correct_size_is_accepted(self):
        generated = Image.new('RGB', (1024, 1024), (110, 120, 130))
        ImageDraw.Draw(generated).rectangle(
            (120, 120, 830, 830), fill=(190, 200, 210)
        )
        evidence = validate_generated_image(
            generated, expected_size=(1024, 1024)
        )
        self.assertEqual(evidence['width'], 1024)

    def test_wrong_dimensions_are_rejected(self):
        generated = Image.new('RGB', (512, 512), (100, 120, 130))
        ImageDraw.Draw(generated).rectangle((50, 50, 450, 450), fill=(190, 200, 210))
        reference = Image.new('RGB', (448, 576), (100, 120, 130))
        with self.assertRaisesRegex(ValueError, 'size does not match'):
            validate_generated_image(generated, reference)


if __name__ == '__main__':
    unittest.main()
