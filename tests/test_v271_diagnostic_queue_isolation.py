"""Regression: no-AI diagnostics must remain usable if AI queue is blocked."""
import ast
import unittest
from pathlib import Path


class DiagnosticQueueIsolationTests(unittest.TestCase):
    def test_reference_callbacks_are_not_queued(self):
        source = (
            Path(__file__).resolve().parents[1] / 'app' / 'generate.py'
        ).read_text(encoding='utf-8')
        tree = ast.parse(source)
        named = {}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for keyword in node.keywords:
                if keyword.arg != 'api_name':
                    continue
                if isinstance(keyword.value, ast.Constant):
                    named[keyword.value.value] = {
                        k.arg: k.value for k in node.keywords
                    }
        for name in ('kiem_tra_truyen_anh', 'kiem_tra_render_doc_lap'):
            with self.subTest(name=name):
                self.assertIn(name, named)
                queue = named[name].get('queue')
                self.assertIsInstance(queue, ast.Constant)
                self.assertIs(queue.value, False)


if __name__ == '__main__':
    unittest.main()
