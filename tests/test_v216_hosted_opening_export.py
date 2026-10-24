import tempfile
import unittest
from pathlib import Path

from app.canonical_3d_export import export_building_glb
from app.schematic_architecture import create_schematic
from app.schematic_roof import add_gable_roof
from app.schematic_slabs import add_schematic_slabs
from app.wall_openings import add_wall_opening


class HostedOpeningExportTests(unittest.TestCase):
    def test_hosted_door_and_window_remove_correct_volume(self):
        import trimesh

        original = add_gable_roof(add_schematic_slabs(
            create_schematic('project_216', 12, 8, 3.2)))
        with_door = add_wall_opening(
            original, 'W01_01', 'DOOR_01', 2, 0, 1, 2.1)
        with_both = add_wall_opening(
            with_door, 'W01_03', 'WINDOW_01', 2, 0.9, 1.5, 1.3)
        self.assertEqual(with_both['entities'][-2]['category'], 'door')
        self.assertEqual(with_both['entities'][-1]['category'], 'window')

        def get_volume(path):
            scene = trimesh.load(path, force='scene')
            return sum(abs(mesh.volume) for mesh in scene.dump())

        with tempfile.TemporaryDirectory() as directory:
            files = [Path(directory) / f'case_{i}.glb' for i in range(3)]
            for project, filepath in zip(
                    (original, with_door, with_both), files):
                export_building_glb(project, filepath)
                self.assertEqual(filepath.read_bytes()[:4], b'glTF')
            base_volume, door_volume, both_volume = [
                get_volume(filepath) for filepath in files]
            self.assertAlmostEqual(
                base_volume - door_volume, 1.0 * 2.1 * 0.2, delta=0.001)
            self.assertAlmostEqual(
                door_volume - both_volume, 1.5 * 1.3 * 0.2, delta=0.001)

    def test_invalid_host_and_overlap_fail_before_export(self):
        project = create_schematic('project_216', 12, 8, 3.2)
        with self.assertRaises(ValueError):
            add_wall_opening(project, 'MISSING', 'DOOR', 2, 0, 1, 2)
        door = add_wall_opening(project, 'W01_01', 'DOOR', 2, 0, 1, 2)
        with self.assertRaises(ValueError):
            add_wall_opening(door, 'W01_01', 'WINDOW', 2.2, 0.8, 1, 1)
