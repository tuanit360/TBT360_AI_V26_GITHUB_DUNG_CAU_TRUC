import tempfile
import unittest
from pathlib import Path
from app.schematic_architecture import create_schematic
from app.schematic_slabs import add_schematic_slabs, slab_mesh_data
from app.canonical_3d_export import export_building_glb


class V176BuildingGeometryTests(unittest.TestCase):
    def test_slabs_share_levels_and_glb_nodes(self):
        import trimesh
        base = create_schematic('office_176', 12, 8, 3.2, 2)
        model = add_schematic_slabs(base)
        self.assertEqual(len(base['entities']), 8)
        self.assertEqual([x[0] for x in slab_mesh_data(model)], ['SLAB_L01', 'SLAB_L02'])
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'building.glb'
            metadata = export_building_glb(model, output)
            self.assertEqual(len(metadata['slab_entity_ids']), 2)
            scene = trimesh.load(str(output), force='scene')
            self.assertGreaterEqual(len(scene.geometry), 10)
            self.assertTrue(output.read_bytes().startswith(b'glTF'))

    def test_duplicate_slabs_and_invalid_thickness_rejected(self):
        model = create_schematic('office_176', 12, 8, 3.2)
        with self.assertRaises(ValueError):
            add_schematic_slabs(model, -1)
        with self.assertRaises(ValueError):
            add_schematic_slabs(add_schematic_slabs(model))
