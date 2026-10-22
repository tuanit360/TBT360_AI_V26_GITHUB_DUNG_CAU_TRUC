import ast
import unittest
from pathlib import Path
from app.schematic_architecture import create_schematic
from app.schematic_slabs import add_schematic_slabs
from app.schematic_roof import add_gable_roof
from app.wall_openings import add_wall_opening
from app.canonical_3d_export import canonical_wall_mesh


class V226SampleFirstTests(unittest.TestCase):
    def test_first_workflow_contains_real_sample_and_preflight(self):
        file = Path(__file__).resolve().parents[1] / 'app' / 'generate.py'
        content = file.read_text(encoding='utf-8')
        ast.parse(content)
        self.assertIn('DÙNG DỰ ÁN MẪU', content)
        self.assertIn('KIỂM TRA GPU / MODEL', content)
        self.assertIn("export_schematic('OFFICE_001_DEMO', 12.0, 9.0, 3.2, 2)", content)
        version_file = file.parents[1] / 'APP_VERSION.txt'
        import re
        version_match = re.search(r'\\bV\\d+\\b', version_file.read_text(encoding='utf-8'))
        self.assertIsNotNone(version_match, 'Thiếu mã phiên bản phát hành')
        self.assertIn('BIM AI Kiến Trúc 360 ' + version_match.group() + ' ·', content)

    def test_sample_canonical_assembly_contains_real_3d_wall_openings(self):
        doc = create_schematic('OFFICE_001_DEMO', 12, 9, 3.2, 2)
        doc = add_schematic_slabs(doc)
        doc = add_gable_roof(doc)
        doc = add_wall_opening(doc, 'W01_01', 'DOOR_01', 1, 0, 1, 2.1)
        doc = add_wall_opening(doc, 'W01_03', 'WINDOW_01', 2, 0.9, 1.5, 1.3)
        categories = {item['category'] for item in doc['entities']}
        self.assertTrue({'wall', 'slab', 'roof', 'door', 'window'} <= categories)
        self.assertEqual(len(doc['levels']), 2)
        self.assertGreater(len(canonical_wall_mesh(doc)['triangles']), 0)
