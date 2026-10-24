import tempfile
import base64
import io
import unittest
from pathlib import Path
from PIL import Image

from app.diagnostic_image_render import render_diagnostic_image, render_image_gallery


class V271InlineImageTests(unittest.TestCase):
    def test_reference_render_embeds_valid_png(self):
        rendered = render_diagnostic_image(Image.new('RGB', (80, 70)))
        self.assertIn('data:image/png;base64,', rendered)
        self.assertNotIn('/file=', rendered)

    def test_generated_gallery_embeds_png_and_escapes_caption(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'generated.png'
            Image.new('RGB', (120, 90)).save(path)
            markup = render_image_gallery([(str(path), '<script>unsafe</script>')])
            self.assertIn('data:image/png;base64,', markup)
            self.assertIn('&lt;script&gt;', markup)
            self.assertNotIn('<script>', markup)

    def test_ai_preview_keeps_high_resolution_and_view_disclaimer(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'large.png'
            Image.new('RGB', (1600, 900)).save(path)
            markup = render_image_gallery([(str(path), 'Góc mặt tiền')])
            encoded = markup.split('data:image/png;base64,', 1)[1].split('"', 1)[0]
            with Image.open(io.BytesIO(base64.b64decode(encoded))) as preview:
                self.assertEqual(preview.size, (1024, 576))
            self.assertIn('Không tự suy diễn mặt sau', markup)

    def test_gallery_reports_missing_output(self):
        with self.assertRaises(ValueError):
            render_image_gallery([('nonexistent.png', 'missing')])


if __name__ == '__main__':
    unittest.main()
