import unittest
from app.schematic_architecture import create_schematic
from app.canonical_3d_export import canonical_wall_mesh


class V171Canonical3DTests(unittest.TestCase):
    def test_wall_triangles_and_stable_entity_ids(self):
        model = create_schematic('office_171', 12, 8, 3.2, 2)
        mesh = canonical_wall_mesh(model)
        self.assertEqual(len(mesh['wall_entity_ids']), 8)
        self.assertEqual(len(mesh['vertices_m']), 64)
        self.assertEqual(len(mesh['triangles']), 96)
        self.assertEqual(mesh['wall_entity_ids'][0], 'W01_01')
        self.assertFalse(mesh['verified'])

    def test_bad_wall_origin_rejected(self):
        model = create_schematic('office_171', 12, 8, 3.2)
        model['entities'][0]['geometry']['endpoint'] = model['entities'][0]['geometry']['origin'][:]
        with self.assertRaises(ValueError):
            canonical_wall_mesh(model)
