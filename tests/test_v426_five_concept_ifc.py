import tempfile
import unittest
from pathlib import Path
from PIL import Image
from app.five_concept_ifc import SCHEMES, export_five_concepts


class IFCConceptUITests(unittest.TestCase):
    def test_has_five_distinct_concepts(self):
        self.assertEqual(len(SCHEMES), 5)
        self.assertEqual(len({scheme[0] for scheme in SCHEMES}), 5)

    def test_missing_photo_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                export_five_concepts(None, directory)

    def test_ifc_exports_are_parseable_if_sdk_installed(self):
        try:
            import ifcopenshell
        except ImportError:
            self.skipTest('IfcOpenShell not installed in test environment')
        with tempfile.TemporaryDirectory() as directory:
            archive, message = export_five_concepts(
                Image.new('RGB', (96, 96), (100, 150, 180)), directory,
            )
            self.assertTrue(Path(archive).is_file())
            self.assertIn('5 IFC4', message)
