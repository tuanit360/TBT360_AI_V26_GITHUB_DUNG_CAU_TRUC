import copy
import unittest

from app.schematic_architecture import create_schematic
from app.schematic_slabs import add_schematic_slabs
from app.schematic_roof import add_gable_roof
from app.wall_openings import add_wall_opening
from app.schematic_delivery_audit import audit_schematic_building


class V241DeliveryAuditTests(unittest.TestCase):
    def setUp(self):
        model = create_schematic('office_241', 12, 9, 3.2, 2)
        model = add_schematic_slabs(model)
        model = add_gable_roof(model)
        self.model = add_wall_opening(model, 'W01_01', 'DOOR_01', 1, 0, 1, 2.1)

    def test_concept_assembly_audits_and_preserves_provenance(self):
        report = audit_schematic_building(self.model)
        self.assertEqual(report['so_tang'], 2)
        self.assertEqual(report['dien_tich_san_m2'], 216)
        self.assertEqual(report['so_tuong'], 8)
        self.assertEqual(report['so_san'], 2)
        self.assertFalse(report['da_kiem_tra_ifc'])

    def test_wall_mutation_fails_before_export(self):
        wrong = copy.deepcopy(self.model)
        wrong['entities'][0]['geometry']['endpoint'][0] = 4.0
        with self.assertRaisesRegex(ValueError, 'Hình học tường'):
            audit_schematic_building(wrong)

    def test_missing_slab_fails(self):
        wrong = copy.deepcopy(self.model)
        wrong['entities'] = [e for e in wrong['entities'] if e['id'] != 'SLAB_L02']
        with self.assertRaisesRegex(ValueError, 'Thiếu sàn'):
            audit_schematic_building(wrong)

    def test_level_mismatch_fails(self):
        wrong = copy.deepcopy(self.model)
        wrong['levels'][1]['elevation'] = 4.0
        with self.assertRaises(ValueError):
            audit_schematic_building(wrong)
