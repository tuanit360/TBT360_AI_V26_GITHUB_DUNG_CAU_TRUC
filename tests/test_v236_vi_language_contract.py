import unittest
from pathlib import Path

from app.vi_labels import IMAGE_ROLES, image_role_code, translate_report


class V236VietnameseUIContractTests(unittest.TestCase):
    def test_all_user_image_choices_are_vietnamese(self):
        self.assertEqual(len(IMAGE_ROLES), 5)
        self.assertEqual(image_role_code('Ảnh phối cảnh ngoại thất'), 'exterior_perspective')
        self.assertEqual(image_role_code('Bản vẽ mặt bằng'), 'floorplan')
        self.assertTrue(all(any(ord(c) > 127 for c in label) for label in IMAGE_ROLES))
        with self.assertRaises(ValueError):
            image_role_code('floorplan')

    def test_translation_keeps_original_api_json(self):
        original = {'project_id': 'office_236',
                    'model_inference_performed': False,
                    'status': 'unknown'}
        display = translate_report(original)
        self.assertEqual(display['trang_thai'], 'Chưa có thông tin')
        self.assertEqual(display['du_lieu_ky_thuat'], original)
        self.assertFalse(display['da_chay_suy_luan_ai'])

    def test_user_dropdown_never_exposes_english_role_codes(self):
        source = (Path(__file__).resolve().parents[1] /
                  'app' / 'generate.py').read_text(encoding='utf-8')
        compile(source, 'app/generate.py', 'exec')
        self.assertIn('choices=list(IMAGE_ROLES)', source)
        self.assertIn('image_role_code(role)', source)
        self.assertNotIn("['exterior_perspective', 'interior', 'floorplan'", source)
