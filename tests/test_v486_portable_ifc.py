import unittest
from pathlib import Path


class PortableIFCTest(unittest.TestCase):
    def test_frozen_build_has_real_ifc_gate(self):
        root = Path(__file__).resolve().parents[1]
        code = (root / 'tools/build_release.py').read_text(encoding='utf-8')
        runner = (root / 'run_portable.py').read_text(encoding='utf-8')
        self.assertIn("'--ifc-export-self-test'", code)
        self.assertIn("test_frozen_ifc_export(root)", runner)
        self.assertIn("'--collect-all', 'ifcopenshell'", code)

    def test_probe_exports_five_ifc_when_installed(self):
        try:
            import ifcopenshell
        except ImportError:
            self.skipTest('IfcOpenShell is supplied in Windows build')
        from app.ifc_portable_smoke import test_frozen_ifc_export
        with __import__('tempfile').TemporaryDirectory() as folder:
            result = test_frozen_ifc_export(folder)
            self.assertEqual(result['status'], 'PASS_REAL_IFC_EXPORT')
            self.assertEqual(result['models'], 5)


if __name__ == '__main__':
    unittest.main()
