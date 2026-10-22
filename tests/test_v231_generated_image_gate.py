import unittest

from PIL import Image

from app.generated_image_gate import validate_generated_image


class V231GeneratedImageGateTests(unittest.TestCase):
    def test_black_image_is_blocked_before_export(self):
        with self.assertRaisesRegex(ValueError, 'nearly black'):
            validate_generated_image(Image.new('RGB', (512, 512), (0, 0, 0)))

    def test_blank_gray_output_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'visually blank'):
            validate_generated_image(Image.new('RGB', (512, 512), (128, 128, 128)))

    def test_nonblank_concept_image_has_evidence(self):
        img = Image.new('RGB', (512, 512), 'skyblue')
        for x in range(200, 300):
            for y in range(150, 400):
                img.putpixel((x, y), (40, 70, 90))
        result = validate_generated_image(img, img)
        self.assertEqual(result['width'], 512)
        self.assertFalse(result['black_output_rejected'])

    def test_wrong_output_size_fails(self):
        with self.assertRaisesRegex(ValueError, 'does not match'):
            validate_generated_image(Image.new('RGB', (512, 512), 'red'),
                                     Image.new('RGB', (256, 256), 'red'))
