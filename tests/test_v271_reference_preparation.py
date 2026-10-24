"""Reference preparation regression: EXIF, transparent PNG and no-crop mode."""
import unittest
from PIL import Image
from app.generate import prepare_image, dimensions


class ReferencePreparationTests(unittest.TestCase):
    def test_transparent_png_gets_neutral_background(self):
        source = Image.new('RGBA', (400, 300), (0, 0, 0, 0))
        result, digest = prepare_image(source, 'Ngang 4:3', 'Giữ đủ ảnh (thêm viền)')
        self.assertEqual(result.size, dimensions('Ngang 4:3'))
        self.assertEqual(result.getpixel((result.width // 2, result.height // 2)), (230, 231, 230))
        self.assertEqual(len(digest), 64)

    def test_opaque_rgba_preserves_color(self):
        source = Image.new('RGBA', (512, 512), (180, 80, 30, 255))
        result, _ = prepare_image(source, 'Vuông 1:1', 'Giữ đủ ảnh (thêm viền)')
        self.assertEqual(result.getpixel((256, 256)), (180, 80, 30))

    def test_keep_full_image_has_neutral_borders(self):
        source = Image.new('RGB', (512, 100), (40, 80, 120))
        result, _ = prepare_image(source, 'Vuông 1:1', 'Giữ đủ ảnh (thêm viền)')
        self.assertEqual(result.getpixel((256, 0)), (230, 231, 230))
        self.assertEqual(result.getpixel((256, 256)), (40, 80, 120))


if __name__ == '__main__':
    unittest.main()
