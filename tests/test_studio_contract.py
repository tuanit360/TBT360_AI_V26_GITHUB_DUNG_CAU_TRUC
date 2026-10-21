import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class StudioContract(unittest.TestCase):
    def test_python_parses(self):
        for path in ROOT.rglob('*.py'):
            if 'vendor' not in path.parts:
                ast.parse(path.read_text(encoding='utf-8'),filename=str(path))

    def test_presets_and_export(self):
        source=(ROOT/'app/generate.py').read_text(encoding='utf-8')
        for token in ('PRESETS =', 'STYLE =', 'apply_preset(', 'postprocess_image(',
                      "'guidance_scale'", "'output_scale'", "'seed'", 'gr.Progress()'):
            self.assertIn(token, source)
        self.assertNotIn('guidance_scale=7.0,',source)

if __name__=='__main__':
    unittest.main()
