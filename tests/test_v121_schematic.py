import unittest
from app.schematic_architecture import create_schematic, render_views
from app.bim_transaction import validate_document


class SchematicBimTests(unittest.TestCase):
    def test_shared_wall_data_and_two_derived_views(self):
        doc = create_schematic('office_121', 12, 8, 3.2, 3)
        self.assertEqual(len(doc['entities']), 12)
        self.assertEqual(len(doc['levels']), 3)
        self.assertEqual(len({entity['id'] for entity in doc['entities']}), 12)
        self.assertEqual(len(validate_document(doc)['entities']), 12)
        views = render_views(doc)
        self.assertIn('plan.svg', views)
        self.assertIn('front_elevation.svg', views)
        self.assertFalse(doc['ifc_export_ready'])

    def test_invalid_dimensions_blocked(self):
        with self.assertRaises(ValueError):
            create_schematic('office_121', 0, 8, 3.2, 3)
        with self.assertRaises(ValueError):
            create_schematic('office_121', 12, 8, 3.2, 21)
