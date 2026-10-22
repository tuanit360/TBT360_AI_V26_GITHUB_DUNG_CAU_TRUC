import json
import tempfile
import unittest
from pathlib import Path
from app.canonical_bim_contract import build_handoff, save_handoff
from app.bim_handoff_verify import verify_saved_handoff


class V96CanonicalRegressionTests(unittest.TestCase):
    def setUp(self):
        self.levels = [{'id': 'L1', 'elevation': 0}, {'id': 'L2', 'elevation': 3.3}]
        self.wall = {'id': 'W1', 'category': 'wall', 'level_id': 'L1',
                     'geometry': {'origin': [0, 0, 0]}, 'verification': 'concept'}
        self.door = {'id': 'D1', 'category': 'door', 'level_id': 'L1', 'host_id': 'W1'}

    def test_hosted_element_and_roundtrip(self):
        data = build_handoff('office_96', level_ids=self.levels, elements=[self.wall, self.door])
        with tempfile.TemporaryDirectory() as folder:
            path = save_handoff(folder, data)
            report = verify_saved_handoff(path)
            self.assertTrue(report['valid'])
            self.assertEqual(report['entities'], 2)
            data['ifc_export_ready'] = True
            path.write_text(json.dumps(data))
            self.assertFalse(verify_saved_handoff(path)['valid'])

    def test_orphan_host_and_cycles_blocked(self):
        orphan = dict(self.door, host_id='missing')
        with self.assertRaisesRegex(ValueError, 'Host'):
            build_handoff('office_96', level_ids=self.levels, elements=[self.wall, orphan])
        wall = dict(self.wall, host_id='D1')
        door = dict(self.door, host_id='W1')
        with self.assertRaisesRegex(ValueError, 'chu kỳ'):
            build_handoff('office_96', level_ids=self.levels, elements=[wall, door])

    def test_invalid_real_geometry_values_blocked(self):
        with self.assertRaises(ValueError):
            build_handoff('office_96', level_ids=[{'id': 'L1', 'elevation': float('nan')}])
        bad = dict(self.wall, geometry={'origin': [0, float('inf'), 1]})
        with self.assertRaises(ValueError):
            build_handoff('office_96', level_ids=self.levels, elements=[bad])
        unmeasured = dict(self.door, verification='geometry_validated')
        with self.assertRaises(ValueError):
            build_handoff('office_96', level_ids=self.levels, elements=[self.wall, unmeasured])
