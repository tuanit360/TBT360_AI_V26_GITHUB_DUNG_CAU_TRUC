import tempfile
import unittest
from pathlib import Path
from PIL import Image
from app.ifc_isolated_bridge import export_isolated_ifc


class IsolatedIFCExportTests(unittest.TestCase):
    def test_missing_image_is_handled(self):
        with tempfile.TemporaryDirectory() as root:
            archive, status = export_isolated_ifc(None, root)
            self.assertIsNone(archive)
            self.assertIn('tải ảnh', status)

    def test_source_subprocess_real_ifc(self):
        try:
            import ifcopenshell
        except ImportError:
            self.skipTest('IfcOpenShell is bundled in Windows CI')
        with tempfile.TemporaryDirectory() as root:
            archive, status = export_isolated_ifc(
                Image.new('RGB', (96, 96), (100, 140, 150)), root,
            )
            self.assertIsNotNone(archive, status)
            self.assertTrue(Path(archive).is_file())
            self.assertTrue(Path(archive).is_file())


if __name__ == '__main__':
    unittest.main()
