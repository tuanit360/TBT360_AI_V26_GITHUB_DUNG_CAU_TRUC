import unittest
from PIL import Image
from app.reference_image_check import inspect_reference_image


class ReferenceImageTests(unittest.TestCase):
    def test_rgb_upload_is_echoed(self):
        preview, message = inspect_reference_image(Image.new('RGB', (900, 675)))
        self.assertEqual(preview.size, (900, 675))
        self.assertIn('ĐÃ ĐỌC ẢNH', message)
        self.assertIn('KHÔNG phải ảnh AI', message)

    def test_invalid_input_has_clear_message(self):
        preview, message = inspect_reference_image(None)
        self.assertIsNone(preview)
        self.assertIn('Hãy tải lại ảnh', message)

    def test_tiny_image_fails_without_crash(self):
        preview, message = inspect_reference_image(Image.new('RGB', (16, 16)))
        self.assertIsNone(preview)
        self.assertIn('quá nhỏ', message)


if __name__ == '__main__':
    unittest.main()
