import io
import json
import unittest
from app.windows_console import print_portable_json


class LegacyWindowsConsoleTests(unittest.TestCase):
    def test_vietnamese_failure_can_print_to_cp1252(self):
        output = io.TextIOWrapper(
            io.BytesIO(), encoding='cp1252', errors='strict',
        )
        print_portable_json({'message': 'Không đủ bộ nhớ để sinh ảnh'}, output)
        output.seek(0)
        text = output.read()
        self.assertTrue(text.isascii())
        self.assertEqual(
            json.loads(text)['message'], 'Không đủ bộ nhớ để sinh ảnh'
        )

    def test_ascii_json_is_reversible(self):
        stream = io.StringIO()
        print_portable_json({'code': 'INVALID_INPUT', 'message': 'Lỗi đầu vào'}, stream)
        self.assertEqual(json.loads(stream.getvalue())['message'], 'Lỗi đầu vào')


if __name__ == '__main__':
    unittest.main()
