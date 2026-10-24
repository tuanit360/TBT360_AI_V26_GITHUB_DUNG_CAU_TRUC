import ast
import unittest
from pathlib import Path

class IFCProminenceTest(unittest.TestCase):
    def test_ifc_button_immediately_after_upload(self):
        source = (Path(__file__).resolve().parents[1] / 'app' / 'generate.py').read_text(encoding='utf-8')
        ast.parse(source)
        start = source.index("reference=gr.Image(label='Ảnh công trình tham chiếu'")
        button = source.index("'XUẤT 5 PHƯƠNG ÁN IFC CÙNG CÔNG TRÌNH'", start)
        diagnostic = source.index("gr.Markdown('### Kiểm tra ảnh và chẩn đoán tại chỗ')",start)
        self.assertLess(button, diagnostic)
        self.assertIn('inputs=reference', source)
