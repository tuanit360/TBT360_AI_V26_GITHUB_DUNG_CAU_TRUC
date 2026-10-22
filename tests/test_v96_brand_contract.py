import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BIMAI360BrandContractTests(unittest.TestCase):
    def test_display_and_version_marker(self):
        app = (ROOT / 'app/generate.py').read_text(encoding='utf-8')
        version = (ROOT / 'APP_VERSION.txt').read_text(encoding='utf-8')
        self.assertIn('BIM AI Kiến Trúc 360 V111', app)
        self.assertIn('BIM AI Kiến Trúc 360 V111', version)

    def test_one_canonical_portable_name(self):
        builder = (ROOT / 'tools/build_release.py').read_text(encoding='utf-8')
        workflow = (ROOT / '.github/workflows/windows-build.yml').read_text(encoding='utf-8')
        for file in (builder, workflow):
            self.assertIn('BIMAI360.exe', file)
        self.assertIn("BIMAI360_V111_PORTABLE_WINDOWS_X64_{args.profile.upper()}", builder)
        self.assertIn('BIMAI360_V111_PORTABLE_WINDOWS_X64_CPU', workflow)
        self.assertIn('BIMAI360_HOME', (ROOT / 'run_portable.py').read_text(encoding='utf-8'))
