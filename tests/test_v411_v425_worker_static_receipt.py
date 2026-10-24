import ast
import unittest
from pathlib import Path


class WorkerReceiptStaticTests(unittest.TestCase):
    def test_no_dynamic_module_import_in_worker_receipt(self):
        source = (Path(__file__).resolve().parents[1] /
                  'app' / 'isolated_image_worker.py').read_text(encoding='utf-8')
        ast.parse(source)
        self.assertNotIn("__import__('app.worker_output_contract'", source)
        self.assertIn("'sha256': sha256_file(archive)", source)

    def test_parent_verifies_receipt(self):
        source = (Path(__file__).resolve().parents[1] /
                  'app' / 'isolated_image_bridge.py').read_text(encoding='utf-8')
        self.assertIn('verify_worker_receipt(report, run_dir)', source)
        self.assertIn('kiểm tra PNG/ZIP thất bại', source)


if __name__ == '__main__':
    unittest.main()
