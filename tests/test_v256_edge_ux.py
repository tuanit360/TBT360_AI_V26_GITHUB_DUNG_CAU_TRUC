import ast
import unittest
from pathlib import Path
from PIL import Image
from app.structure_guidance import structure_reference


class V256EdgeUXTests(unittest.TestCase):
    def test_source_compiles_and_controls_require_image(self):
        s=(Path(__file__).resolve().parents[1]/'app'/'generate.py').read_text(encoding='utf-8')
        ast.parse(s)
        self.assertIn("structure_preview = gr.Button('TẠO ẢNH BIÊN THAM CHIẾU', variant='primary', interactive=False)",s)
        self.assertIn("structure_input.change(",s)
        self.assertIn("gr.update(interactive=has_image)",s)
        self.assertIn("value='Xem nhanh · ít VRAM'",s)
        self.assertIn("count=gr.Slider(1,4,value=1",s)

    def test_real_edge_creation_and_input_guard(self):
        with self.assertRaisesRegex(ValueError,'Chọn ảnh'):
            structure_reference(None,80)
        picture=Image.new('RGB',(256,256),'white')
        for x in range(50,200):
            for y in range(50,200):
                picture.putpixel((x,y),(0,0,0))
        edge=structure_reference(picture,80)
        self.assertEqual(edge.size,picture.size)
        self.assertTrue(any(v>0 for v in edge.convert('L').getextrema()))
