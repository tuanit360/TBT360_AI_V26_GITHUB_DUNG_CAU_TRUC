import unittest
from pathlib import Path


class V271PortableSurfaceTests(unittest.TestCase):
    def test_portable_has_no_obsolete_launcher_collection(self):
        source = (Path(__file__).resolve().parents[1] /
                  'tools' / 'build_release.py').read_text(encoding='utf-8')
        self.assertIn("for script in target.glob('*.bat'):", source)
        self.assertIn("CHAY_BIMAI360_CPU_KHONG_CUDA.bat", source)
        self.assertIn("MO_LOG_KHONG_CAN_UI.bat", source)
        self.assertNotIn("shutil.copy2(ROOT / 'CHAY_OFFLINE_WINDOWS.bat'", source)

    def test_cpu_launcher_validates_exe_location(self):
        source = (Path(__file__).resolve().parents[1] /
                  'CHAY_BIMAI360_CPU_KHONG_CUDA.bat').read_text(encoding='utf-8')
        self.assertIn('BIMAI360\\BIMAI360.exe', source)
        self.assertIn('dist\\BIMAI360\\BIMAI360.exe', source)
        self.assertIn('if not exist "%BIMAI_EXE%"', source)
        self.assertIn('BIMAI360_FORCE_CPU=1', source)


if __name__ == '__main__':
    unittest.main()
