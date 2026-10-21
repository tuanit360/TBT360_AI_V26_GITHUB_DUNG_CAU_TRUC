import unittest
from PIL import Image
from app.quality import image_diagnostics, diagnostic_notes


class QualityDiagnosticsTests(unittest.TestCase):
    def test_white_image_flags(self):
        item = image_diagnostics(Image.new('RGB', (800, 600), 'white'))
        self.assertEqual(item['near_white_fraction'], 1.0)
        self.assertTrue(any('near-white' in message for message in diagnostic_notes(item)))

    def test_determinism(self):
        image = Image.new('RGB', (640, 640), (120, 80, 60))
        self.assertEqual(image_diagnostics(image), image_diagnostics(image))

    def test_low_resolution_warning(self):
        item = image_diagnostics(Image.new('RGB', (320, 320), 'gray'))
        self.assertTrue(any('resolution' in message for message in diagnostic_notes(item)))

    def test_does_not_modify_source(self):
        image = Image.new('RGB', (640, 640), (10, 20, 30))
        before = image.tobytes()
        image_diagnostics(image)
        self.assertEqual(before, image.tobytes())


if __name__ == '__main__':
    unittest.main()
