import tempfile
import unittest
from pathlib import Path

import trimesh

from app.schematic_architecture import create_schematic
from app.schematic_slabs import add_schematic_slabs
from app.schematic_roof import add_gable_roof
from app.wall_openings import add_wall_opening
from app.canonical_3d_export import export_building_glb
from app.handoff_mesh_fidelity import (
    expected_solid_volume, validate_reopened_mesh_volume
)


class V251GLBVolumeFidelityTests(unittest.TestCase):
    def test_real_export_matches_wall_slab_and_opening_volume(self):
        model = add_gable_roof(add_schematic_slabs(
            create_schematic('office_251', 12, 9, 3.2, 2)))
        model = add_wall_opening(model, 'W01_01', 'DOOR_01', 1, 0, 1, 2.1)
        model = add_wall_opening(model, 'W01_03', 'WINDOW_01', 2, 0.9, 1.5, 1.3)
        expected = expected_solid_volume(model)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'real.glb'
            export_building_glb(model, path)
            scene = trimesh.load(str(path), force='scene')
            result = validate_reopened_mesh_volume(scene, model)
            self.assertAlmostEqual(result['the_tich_bim_du_kien_m3'], expected, places=4)
            self.assertLess(result['sai_lech_m3'], 0.005)
            wrong = add_wall_opening(model, 'W01_01', 'WINDOW_EXTRA', 5, 1, 1, 1)
            with self.assertRaisesRegex(ValueError, 'không khớp'):
                validate_reopened_mesh_volume(scene, wrong)
