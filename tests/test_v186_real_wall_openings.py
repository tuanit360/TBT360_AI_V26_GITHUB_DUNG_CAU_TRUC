import tempfile
import unittest
from pathlib import Path
from app.schematic_architecture import create_schematic
from app.schematic_slabs import add_schematic_slabs
from app.schematic_roof import add_gable_roof
from app.wall_openings import add_wall_opening, wall_solid_parts
from app.canonical_3d_export import export_building_glb


class V186WallOpeningTests(unittest.TestCase):
    def setUp(self):
        self.base = create_schematic('office_186', 12, 8, 3.2)

    def test_cutout_excludes_void_and_preserves_wall(self):
        model = add_wall_opening(self.base, 'W01_01', 'DOOR_01', 2.0, 0, 1.0, 2.1)
        parts = wall_solid_parts(model, 'W01_01')
        self.assertTrue(parts)
        volume = sum((right-left)*(top-bottom) for left, right, bottom, top in parts)
        self.assertAlmostEqual(volume, 12*3.2 - 1*2.1)
        self.assertEqual(len(self.base['entities']), 4)
        self.assertEqual(model['entities'][-1]['host_id'], 'W01_01')

    def test_overlap_or_wall_escape_rejected(self):
        model = add_wall_opening(self.base, 'W01_01', 'WINDOW_01', 2, 0.8, 1.5, 1.2)
        with self.assertRaises(ValueError):
            add_wall_opening(model, 'W01_01', 'WINDOW_02', 2.5, 1, 1.2, 1)
        with self.assertRaises(ValueError):
            add_wall_opening(model, 'W01_01', 'WINDOW_03', 11.8, 1, 1.2, 1)

    def test_real_glb_opening_roundtrip(self):
        import trimesh
        shell = add_gable_roof(add_schematic_slabs(self.base))
        opened = add_wall_opening(shell, 'W01_01', 'DOOR_01', 2, 0, 1, 2.1)
        with tempfile.TemporaryDirectory() as folder:
            before_path = Path(folder) / 'before.glb'
            after_path = Path(folder) / 'after.glb'
            export_building_glb(shell, before_path)
            export_building_glb(opened, after_path)
            before = trimesh.load(before_path, force='scene')
            after = trimesh.load(after_path, force='scene')
            self.assertTrue(after_path.read_bytes().startswith(b'glTF'))
            self.assertGreater(len(after.geometry), 0)
            # Compare physical mesh volume, avoiding unrelated roof/slab geometry
            # whose bounding boxes naturally include the doorway's location.
            def total_volume(scene):
                return sum(abs(part.volume) for part in scene.dump())
            self.assertAlmostEqual(
                total_volume(before) - total_volume(after),
                1.0 * 2.1 * 0.2,
                delta=0.001)
