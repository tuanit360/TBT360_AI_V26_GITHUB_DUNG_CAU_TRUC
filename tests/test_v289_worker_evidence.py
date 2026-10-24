import tempfile
import unittest
from app.worker_evidence import write_state, read_report


class EvidenceTests(unittest.TestCase):
    def test_stage_roundtrip(self):
        with tempfile.TemporaryDirectory() as root:
            write_state(root, '0123456789abcdef', 'MODEL_LOAD_BEGIN')
            self.assertEqual(read_report(root)['stage'], 'MODEL_LOAD_BEGIN')
            write_state(root, '0123456789abcdef', 'FAILED', 'FAILED', 'MODEL_MISSING')
            self.assertEqual(read_report(root)['code'], 'MODEL_MISSING')

    def test_invalid_stage_cannot_modify_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            write_state(root, 'not-a-job', 'BOOT')
            self.assertEqual(read_report(root)['status'], 'NO_REPORT')


if __name__ == '__main__':
    unittest.main()
