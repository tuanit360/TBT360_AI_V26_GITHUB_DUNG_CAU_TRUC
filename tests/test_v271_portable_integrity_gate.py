import json
import tempfile
import unittest
from pathlib import Path

from tools.verify_portable import verify, verify_release_structure


class V271PortableIntegrityGateTests(unittest.TestCase):
    def test_fails_when_exe_is_missing_even_if_manifest_is_empty(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'manifest.json').write_text('{"files": {}}', encoding='utf-8')
            failures = verify_release_structure(root)
            self.assertTrue(any('BIMAI360.exe' in item for item in failures))

    def test_fails_when_old_bat_is_accidentally_shipped(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'manifest.json').write_text(json.dumps({'files': {}}), encoding='utf-8')
            for filename in (
                'BIMAI360.exe', 'CHAY_BIMAI360_CPU_KHONG_CUDA.bat',
                'MO_LOG_KHONG_CAN_UI.bat',
                'CHAY_BIMAI360_GHI_LOG_LOI.bat', 'README_PORTABLE.md'
            ):
                (root / filename).write_bytes(b'test')
            (root / 'CHAY_OFFLINE_WINDOWS.bat').write_bytes(b'legacy')
            self.assertTrue(any('Obsolete script' in item for item in verify_release_structure(root)))

    def test_minimal_valid_structure_is_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'manifest.json').write_text('{"files": {}}', encoding='utf-8')
            for filename in (
                'BIMAI360.exe', 'CHAY_BIMAI360_CPU_KHONG_CUDA.bat',
                'MO_LOG_KHONG_CAN_UI.bat',
                'CHAY_BIMAI360_GHI_LOG_LOI.bat', 'README_PORTABLE.md'
            ):
                (root / filename).write_bytes(b'test')
            self.assertEqual(verify_release_structure(root), [])


if __name__ == '__main__':
    unittest.main()
