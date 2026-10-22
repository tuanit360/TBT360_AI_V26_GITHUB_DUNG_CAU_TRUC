import unittest
from pathlib import Path
from app.generation_failures import explain_generation_failure, has_prompt


class V266GenerationErrorTests(unittest.TestCase):
    def test_classified_failures_are_vietnamese_and_safe(self):
        self.assertIn('mô hình', explain_generation_failure(
            RuntimeError('Cannot load because not found in cache')))
        self.assertIn('bộ nhớ', explain_generation_failure(
            RuntimeError('CUDA out of memory')))
        message = explain_generation_failure(
            RuntimeError('token=SECRET123 /home/private/secret.txt'))
        self.assertNotIn('SECRET123', message)
        self.assertNotIn('/home/private', message)

    def test_editable_sample_is_real_value_not_placeholder(self):
        source = (Path(__file__).resolve().parents[1] /
                  'app' / 'generate.py').read_text(encoding='utf-8')
        compile(source, 'app/generate.py', 'exec')
        self.assertIn("value='Contemporary office building", source)
        self.assertIn("start.click(create_with_feedback", source)
        self.assertIn('explain_generation_failure(exc)', source)
        self.assertIn("'KHÔNG TẠO ĐƯỢC PHƯƠNG ÁN: '", source)
        self.assertIn("'CHƯA THỂ SINH ẢNH: Thiếu checkpoint SD1.5 '", source)
        self.assertIn('record_operation(ROOT, \'generate\', \'failed\')', source)
        self.assertTrue(has_prompt('Nhà hai tầng'))
        self.assertFalse(has_prompt('   '))
