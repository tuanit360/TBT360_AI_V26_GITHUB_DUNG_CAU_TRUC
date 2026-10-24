import unittest
from PIL import Image
from app.reference_fallback import fallback_reference_preview


class FallbackReferenceTests(unittest.TestCase):
    def test_failed_generation_shows_source_without_cuda(self):
        source = Image.new('RGB', (320, 220), (24, 96, 150))
        failure = ('<p>AI failed</p>', None, 'CUDA unavailable', 'original log')
        preview, archive, status, log = fallback_reference_preview(source, failure)
        self.assertIn('KHÔNG PHẢI ẢNH AI', preview)
        self.assertIn('data:image/png;base64,', preview)
        self.assertIsNone(archive)
        self.assertEqual(status, 'CUDA unavailable')
        self.assertEqual(log, 'original log')

    def test_success_is_not_modified(self):
        result = ('real ai HTML', 'result.zip', 'PASS', 'log')
        source = Image.new('RGB', (30, 30))
        self.assertEqual(fallback_reference_preview(source, result), result)

    def test_missing_source_keeps_error(self):
        result = ('AI error', None, 'CUDA issue', 'log')
        self.assertEqual(fallback_reference_preview(None, result), result)


if __name__ == '__main__':
    unittest.main()
