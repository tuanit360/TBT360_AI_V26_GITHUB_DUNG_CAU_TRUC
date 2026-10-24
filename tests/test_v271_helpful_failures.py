import unittest
from app.generation_failures import explain_generation_failure


class V271HelpfulErrorsTests(unittest.TestCase):
    def test_corrupted_archive_has_actionable_reason(self):
        reason = explain_generation_failure(ValueError('Generated ZIP failed CRC check'))
        self.assertIn('ZIP', reason)
        self.assertIn('hỏng', reason)

    def test_permissions_recommend_extracted_portable(self):
        reason = explain_generation_failure(PermissionError('Permission denied'))
        self.assertIn('quyền ghi', reason)
        self.assertIn('giải nén', reason)

    def test_generic_message_points_to_real_log(self):
        reason = explain_generation_failure(ValueError('unexpected numeric failure'))
        self.assertIn('logs/runtime_errors.log', reason)
        self.assertNotIn('Tài khoản', reason)


if __name__ == '__main__':
    unittest.main()
