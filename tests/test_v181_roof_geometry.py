import tempfile
import unittest
from pathlib import Path
from app.schematic_architecture import create_schematic
from app.schematic_slabs import add_schematic_slabs
from app.schematic_roof import add_gable_roof, gable_mesh
from app.canonical_3d_export import export_building_glb


class V181RoofGeometryTests(unittest.TestCase):
    def test_raised_ridge_and_glb_roundtrip(self):
        import trimesh
        model = add_gable_roof(add_schematic_slabs(
            create_schematic('office_181', 12, 8, 3.2, 2)), 30)
        mesh = gable_mesh(model)
        self.assertEqual(len(mesh['triangles']), 4)
        self.assertGreater(mesh['vertices_m'][1][2], mesh['vertices_m'][0][2])
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'roof.glb'
            summary = export_building_glb(model, target)
            self.assertEqual(summary['roof_entity_ids'], ['ROOF_MAIN'])
            reopened = trimesh.load(str(target), force='scene')
            self.assertIn('ROOF_MAIN', reopened.geometry)

    def test_pitch_validation_and_duplicate_roof(self):
        model = create_schematic('office_181', 12, 8, 3.2)
        with self.assertRaises(ValueError):
            add_gable_roof(model, 90)
        with self.assertRaises(ValueError):
            add_gable_roof(add_gable_roof(model))
