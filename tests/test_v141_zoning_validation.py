import copy
import unittest
from app.schematic_zoning import add_two_zone_sketch
from app.zoning_validation import validate_zoning


class V141ZoningValidationTests(unittest.TestCase):
    def setUp(self):
        self.model = add_two_zone_sketch('office_141', 12, 8)

    def test_correct_area_and_partition(self):
        report = validate_zoning(self.model)
        self.assertEqual(report['zone_areas_m2'], [52.8, 43.2])
        self.assertEqual(report['area_m2'], 96)
        self.assertFalse(report['ifc_export_ready'])

    def test_invalid_partition_fails_without_mutation(self):
        model = copy.deepcopy(self.model)
        model['entities'][-1]['geometry']['origin'][0] = 7
        before = copy.deepcopy(model)
        with self.assertRaises(ValueError):
            validate_zoning(model)
        self.assertEqual(model, before)

    def test_incorrect_zone_bounds_blocked(self):
        model = copy.deepcopy(self.model)
        room = next(item for item in model['entities'] if item['id'] == 'ROOM_B')
        room['geometry']['bounds_xy'][0] = 7.0
        with self.assertRaises(ValueError):
            validate_zoning(model)
