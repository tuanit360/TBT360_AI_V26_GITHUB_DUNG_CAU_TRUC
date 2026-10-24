"""Regression checks for portable startup diagnostics and non-writable folders."""
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_portable


class PortableStartupTests(unittest.TestCase):
    def test_unwritable_temp_path_returns_clear_exit_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'output').write_text('occupied', encoding='utf-8')
            error = io.StringIO()
            with patch.object(run_portable, 'root_directory', return_value=root):
                with patch('sys.stderr', error):
                    status = run_portable.main()
            self.assertEqual(status, 3)
            self.assertIn('Cannot create runtime folder', error.getvalue())

    def test_unwritable_models_directory_returns_clear_exit_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'models').write_text('occupied', encoding='utf-8')
            error = io.StringIO()
            with patch.object(run_portable, 'root_directory', return_value=root):
                with patch('sys.stderr', error):
                    status = run_portable.main()
            self.assertEqual(status, 3)
            self.assertIn('Cannot prepare models', error.getvalue())

    def test_normal_startup_log_uses_real_line_break(self):
        source = (Path(__file__).resolve().parents[1] / 'run_portable.py').read_text(encoding='utf-8')
        self.assertIn("handle.write(f'\\n=== {datetime.now().isoformat()} ===\\n')", source)
        self.assertNotIn("handle.write(f'\\\\n=== ", source)


if __name__ == '__main__':
    unittest.main()
