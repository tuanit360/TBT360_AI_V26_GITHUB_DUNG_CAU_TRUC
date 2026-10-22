import tempfile
import unittest
from pathlib import Path
from app.schematic_architecture import create_schematic
from app.canonical_3d_export import export_wall_glb


class V171GLBRoundtripTests(unittest.TestCase):
    def test_real_glb_scene_roundtrip(self):
        import trimesh
        model = create_schematic('office_171', 12, 8, 3.2, 2)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'schematic.glb'
            mesh = export_wall_glb(model, output)
            self.assertTrue(output.read_bytes().startswith(b'glTF'))
            reopened = trimesh.load(str(output), force='scene')
            self.assertEqual(len(mesh['wall_entity_ids']), 8)
            self.assertGreater(sum(len(part.faces) for part in reopened.geometry.values()), 0)
