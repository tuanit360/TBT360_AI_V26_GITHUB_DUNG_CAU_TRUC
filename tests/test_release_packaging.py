import json
from pathlib import Path
import tempfile
import unittest
from tools.build_release import build_manifest
from tools.verify_portable import verify


class PackagingTests(unittest.TestCase):
    def test_hashes_detect_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'test.dll').write_bytes(b'abc')
            manifest = build_manifest(root, 'cpu')
            (root / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            self.assertFalse(verify(root))
            (root / 'test.dll').write_bytes(b'abd')
            self.assertIn('Hash mismatch: test.dll', verify(root))

    def test_hashes_detect_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'test.dll').write_bytes(b'abc')
            manifest = build_manifest(root, 'cuda')
            (root / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            (root / 'test.dll').unlink()
            self.assertIn('Missing: test.dll', verify(root))
