import unittest
from app.schematic_architecture import create_schematic
from app.schematic_dxf import export_plan_dxf


class V131DxfTests(unittest.TestCase):
    def test_canonical_wall_export_real_meter_units(self):
        model = create_schematic('office_131', 12, 8, 3, 2)
        result = export_plan_dxf(model)
        self.assertEqual(result.count('0\nLINE\n'), 8)
        self.assertIn('$INSUNITS\n70\n6', result)
        self.assertIn('8\nWALL_L01', result)
        self.assertIn('11\n12', result)
        self.assertTrue(result.endswith('0\nEOF\n'))

    def test_missing_geometry_blocks_export(self):
        model = create_schematic('office_131', 12, 8, 3)
        del model['entities'][0]['geometry']['endpoint']
        with self.assertRaises(ValueError):
            export_plan_dxf(model)
