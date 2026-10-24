import json
import tempfile
import unittest
from pathlib import Path

from app.schematic_architecture import create_schematic, render_views
from app.schematic_slabs import add_schematic_slabs
from app.schematic_roof import add_gable_roof
from app.wall_openings import add_wall_opening
from app.schematic_dxf import export_plan_dxf
from app.canonical_3d_export import export_building_glb
from app.handoff_roundtrip import verify_exported_handoff


class V246HandoffRoundtripTests(unittest.TestCase):
    def setUp(self):
        model = create_schematic('office_246', 12, 9, 3.2, 2)
        model = add_schematic_slabs(model)
        model = add_gable_roof(model)
        self.model = add_wall_opening(model, 'W01_01', 'DOOR_01', 1, 0, 1, 2.1)

    def write_exports(self, folder):
        folder = Path(folder)
        (folder / 'canonical_bim_handoff.json').write_text(
            json.dumps(self.model), encoding='utf-8')
        for name, content in render_views(self.model).items():
            (folder / name).write_text(content, encoding='utf-8')
        (folder / 'schematic_plan.dxf').write_text(export_plan_dxf(self.model),
                                                  encoding='utf-8')
        mapping = export_building_glb(self.model, folder / 'schematic_walls.glb')
        (folder / 'schematic_wall_id_mapping.json').write_text(
            json.dumps({
                'canonical_wall_entity_ids': mapping['wall_entity_ids'],
                'canonical_slab_entity_ids': mapping['slab_entity_ids'],
                'canonical_roof_entity_ids': mapping['roof_entity_ids'],
            }), encoding='utf-8')

    def test_all_files_reopen_and_ids_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_exports(tmp)
            report = verify_exported_handoff(tmp, self.model)
            self.assertGreater(report['so_mat_tam_giac_glb'], 0)
            self.assertEqual(len(report['sha256_tung_tep']), 6)
            self.assertFalse(report['xac_minh_ifc'])

    def test_tampered_model_and_missing_export_block_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_exports(tmp)
            file = Path(tmp) / 'schematic_plan.dxf'
            file.unlink()
            with self.assertRaisesRegex(ValueError, 'Thiếu'):
                verify_exported_handoff(tmp, self.model)
            self.write_exports(tmp)
            file = Path(tmp) / 'canonical_bim_handoff.json'
            changed = json.loads(file.read_text(encoding='utf-8'))
            changed['scheme_parameters']['width_m'] = 20
            file.write_text(json.dumps(changed), encoding='utf-8')
            with self.assertRaises(ValueError):
                verify_exported_handoff(tmp, self.model)
