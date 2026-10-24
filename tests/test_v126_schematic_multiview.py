import unittest
from app.schematic_architecture import create_schematic
from app.schematic_multiview import schematic_multiview


class V126MultiviewTests(unittest.TestCase):
    def test_all_views_derived_from_one_canonical_shell(self):
        model = create_schematic('office_126', 12, 8, 3.2, 3)
        views = schematic_multiview(model)
        self.assertEqual(len([name for name in views if name.endswith('.svg')]), 6)
        self.assertTrue(views['view_meta']['views_are_concept_diagrams'])
        self.assertFalse(views['view_meta']['verified_bim_geometry'])
        self.assertIn('240.0', views['front_elevation.svg'])
        self.assertIn('160.0', views['left_elevation.svg'])

    def test_mismatched_geometry_is_rejected(self):
        model = create_schematic('office_126', 12, 8, 3.2, 3)
        model['entities'].pop()
        with self.assertRaises(ValueError):
            schematic_multiview(model)
