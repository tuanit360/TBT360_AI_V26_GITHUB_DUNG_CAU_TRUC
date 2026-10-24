"""Regression for diagnosing Gradio red-error callbacks in frozen Windows builds."""
import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PortableGradioErrorDiagnosticsTests(unittest.TestCase):
    def test_launch_displays_callback_failure_detail(self):
        source = (ROOT / 'app' / 'generate.py').read_text('utf-8')
        tree = ast.parse(source)
        launches = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'launch'
        ]
        self.assertTrue(launches)
        self.assertTrue(any(
            kw.arg == 'show_error'
            and isinstance(kw.value, ast.Constant)
            and kw.value.value is True
            for node in launches for kw in node.keywords
        ))

    def test_gradio_server_traces_are_written_to_local_runtime_log(self):
        source = (ROOT / 'run_portable.py').read_text('utf-8')
        self.assertIn("'gradio'", source)
        self.assertIn("'uvicorn.error'", source)
        self.assertIn('framework_logger.addHandler(runtime_handler)', source)


if __name__ == '__main__':
    unittest.main()
