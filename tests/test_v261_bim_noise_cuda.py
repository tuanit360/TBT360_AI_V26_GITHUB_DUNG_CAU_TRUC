import unittest
from pathlib import Path
from PIL import Image
from app.schematic_architecture import create_schematic
from app.schematic_slabs import add_schematic_slabs
from app.schematic_roof import add_gable_roof
from app.wall_openings import add_wall_opening
from app.schematic_multiview import schematic_multiview
from app.structure_guidance import structure_reference


class V261EndToEndRegression(unittest.TestCase):
    def test_enriched_three_floor_model_has_six_views(self):
        model = create_schematic('office_261',12,8,3.2,3)
        self.assertIn('rear_elevation.svg', schematic_multiview(model))
        model = add_schematic_slabs(model)
        model = add_gable_roof(model)
        model = add_wall_opening(model,'W01_01','DOOR_01',1,0,1,2.1)
        model = add_wall_opening(model,'W01_03','WINDOW_01',2,0.9,1.5,1.3)
        views=schematic_multiview(model)
        self.assertEqual(len([k for k in views if k.endswith('.svg')]),6)

    def test_image_edge_preview_is_nonempty_and_stable(self):
        source = Image.new('RGB',(256,256),'white')
        for x in range(65,190):
            for y in range(65,190):
                source.putpixel((x,y),(10,10,10))
        edge=structure_reference(source,95)
        self.assertEqual(edge.size,(256,256))
        self.assertGreater(edge.convert('L').getbbox() is not None, False)

    def test_cuda_button_is_gated_and_current_source_compiles(self):
        source=(Path(__file__).resolve().parents[1]/'app'/'generate.py').read_text(encoding='utf-8')
        compile(source,'app/generate.py','exec')
        self.assertIn('ui.load(check_advanced_gpu',source)
        self.assertIn('value=95, step=5',source)
