import unittest
from pathlib import Path


class PNGTransportContractTests(unittest.TestCase):
    def test_binary_signature_is_not_escaped_text(self):
        source = (Path(__file__).resolve().parents[1] /
                  'tools' / 'smoke_gradio_image_transport.py').read_text(encoding='utf-8')
        self.assertIn("bytes.fromhex('89504e470d0a1a0a')", source)
        self.assertEqual(bytes.fromhex('89504e470d0a1a0a'), b'\x89PNG\r\n\x1a\n')


if __name__ == '__main__':
    unittest.main()
