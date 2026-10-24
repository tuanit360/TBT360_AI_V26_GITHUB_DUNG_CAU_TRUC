import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from app.five_concept_ifc import SCHEMES, SCHEME_LAYOUTS
from app.ifc_concept_validation import write_verified_archive


class SameBuildingIFCTests(unittest.TestCase):
    def test_same_envelope_five_different_layouts(self):
        self.assertEqual(len(SCHEMES), 5)
        self.assertEqual(len({(v[1], v[2], v[3]) for v in SCHEMES}), 1)
        self.assertEqual(len(set(SCHEME_LAYOUTS.values())), 5)

    def test_ifc_zip_has_no_reference_photo(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'concept'
            folder.mkdir()
            (folder / 'manifest.json').write_text('{}', encoding='utf-8')
            options = []
            for code, *_ in SCHEMES:
                (folder / f'{code}.ifc').write_text('archive fixture', encoding='utf-8')
                options.append({'option': code})
            archive_path = folder.with_suffix('.zip')
            write_verified_archive(folder, archive_path, options)
            with ZipFile(archive_path) as archive:
                names = archive.namelist()
                self.assertEqual(len(names), 6)
                self.assertFalse(any(n.lower().endswith('.png') for n in names))


if __name__ == '__main__':
    unittest.main()
