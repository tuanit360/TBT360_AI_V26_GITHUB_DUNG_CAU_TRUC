import unittest
from app.schematic_zoning import add_two_zone_sketch, zoning_svg
from app.bim_transaction import validate_document


class V136RoomZoningTests(unittest.TestCase):
    def test_two_rooms_partition_and_same_source(self):
        model = add_two_zone_sketch('office_136', 12, 8)
        validate_document(model)
        spaces = [x for x in model['entities'] if x['category'] == 'space']
        self.assertEqual(len(spaces), 2)
        self.assertEqual(spaces[0]['geometry']['bounds_xy'][2], 6.6)
        self.assertFalse(model['zoning']['code_compliance_verified'])
        self.assertIn('132.0', zoning_svg(model))

    def test_invalid_dims_rejected(self):
        with self.assertRaises(ValueError):
            add_two_zone_sketch('office_136', 2, 8)
