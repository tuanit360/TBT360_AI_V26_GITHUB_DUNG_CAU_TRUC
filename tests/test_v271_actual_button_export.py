"""Exercise the exact exported BIM file chain, not isolated subsystems."""
import json
import tempfile
import unittest
from pathlib import Path
from app.schematic_architecture import create_schematic, render_views
from app.schematic_slabs import add_schematic_slabs
from app.schematic_roof import add_gable_roof
from app.wall_openings import add_wall_opening
from app.schematic_delivery_audit import audit_schematic_building
from app.schematic_multiview import schematic_multiview
from app.schematic_dxf import export_plan_dxf
from app.canonical_3d_export import export_building_glb
from app.handoff_roundtrip import verify_exported_handoff


class V271RealBIMCallbackTests(unittest.TestCase):
    def test_three_floor_button_export_end_to_end(self):
        model = create_schematic('office_121',12,8,3.2,3)
        model = add_schematic_slabs(model)
        model = add_gable_roof(model)
        model = add_wall_opening(model,'W01_01','DOOR_01',1,0,1,2.1)
        model = add_wall_opening(model,'W01_03','WINDOW_01',2,0.9,1.5,1.3)
        audit_schematic_building(model)
        files=render_views(model)
        views=schematic_multiview(model)
        views.pop('view_meta')
        files.update(views)
        files['schematic_plan.dxf']=export_plan_dxf(model)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'canonical_bim_handoff.json').write_text(
                json.dumps(model),encoding='utf-8')
            for name,data in files.items():
                (root/name).write_text(data,encoding='utf-8')
            mapping=export_building_glb(model,root/'schematic_walls.glb')
            (root/'schematic_wall_id_mapping.json').write_text(
                json.dumps({
                    'canonical_wall_entity_ids':mapping['wall_entity_ids'],
                    'canonical_slab_entity_ids':mapping['slab_entity_ids'],
                    'canonical_roof_entity_ids':mapping['roof_entity_ids']
                }),encoding='utf-8')
            report=verify_exported_handoff(root,model)
            self.assertGreater(report['so_mat_tam_giac_glb'],0)
            self.assertEqual(report['ket_qua_hinh_hoc']['so_tang'],3)
