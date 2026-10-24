"""The final ZIP gate must accept the required offline diagnostics launcher."""
import ast
import unittest
from pathlib import Path


class PortableZipRequiredScriptsTests(unittest.TestCase):
    def test_required_zip_entries_include_offline_log_launcher(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / 'tools' / 'build_release.py').read_text('utf-8')
        tree = ast.parse(source)
        required_sets = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if any(isinstance(target, ast.Name) and target.id == 'required'
                       for target in node.targets):
                    if isinstance(node.value, ast.Set):
                        required_sets.append({
                            element.value for element in node.value.elts
                            if isinstance(element, ast.Constant)
                        })
        self.assertTrue(required_sets)
        self.assertIn(
            'BIMAI360/CHAY_BIMAI360_GHI_LOG_LOI.bat',
            required_sets[-1],
        )
        self.assertIn('BIMAI360/BIMAI360.exe', required_sets[-1])
        self.assertIn('BIMAI360/SHA256SUMS.txt', required_sets[-1])


if __name__ == '__main__':
    unittest.main()
