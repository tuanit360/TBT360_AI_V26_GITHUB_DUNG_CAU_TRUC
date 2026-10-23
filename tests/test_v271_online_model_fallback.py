"""Prevent regression: online image generation must use cached/downloadable SD1.5."""
import unittest
from pathlib import Path


class V271OnlineModelFallbackTests(unittest.TestCase):
    def test_online_path_is_not_blocked_by_missing_local_sd15(self):
        source = (Path(__file__).resolve().parents[1] / 'app' / 'generate.py').read_text(
            encoding='utf-8'
        )
        callback = source.split('def create_with_feedback(', 1)[1].split(
            'start.click(create_with_feedback', 1
        )[0]
        self.assertIn("if os.environ.get('TBT360_OFFLINE') == '1':", callback)
        self.assertNotIn("if os.environ.get('TBT360_OFFLINE') != '1':", callback)
        self.assertIn('result = create(*arguments, progress=progress)', callback)
        self.assertIn("'stable-diffusion-v1-5/stable-diffusion-v1-5'", source)


if __name__ == '__main__':
    unittest.main()
