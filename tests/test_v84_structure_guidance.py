import hashlib
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from app.structure_guidance import structure_reference, export_structure_package


class V84StructureGuidanceTests(unittest.TestCase):
    def test_edge_map_matches_source_size(self):
        image = Image.new('RGB', (320, 260), 'white')
        control = structure_reference(image, 80)
        self.assertEqual(control.size, image.size)
        with self.assertRaises(ValueError):
            structure_reference(image, 0)

    def test_export_contains_seed_and_checksum(self):
        image = Image.new('RGB', (320, 260), '#7799bb')
        with tempfile.TemporaryDirectory() as temp:
            _, record = export_structure_package(image, temp, threshold=70, seed=1234)
            self.assertEqual(record['seed'], 1234)
            self.assertFalse(record['structure_preservation_verified'])
            control = Path(temp) / 'edge_control.png'
            self.assertEqual(hashlib.sha256(control.read_bytes()).hexdigest(),
                             record['control_sha256'])
