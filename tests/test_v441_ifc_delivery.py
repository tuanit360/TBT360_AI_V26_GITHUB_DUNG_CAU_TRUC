import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from app.ifc_concept_validation import write_verified_archive


class IFCBundleTests(unittest.TestCase):
    def test_bundle_exact_five_ifc_and_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / 'concept'
            folder.mkdir()
            (folder / 'manifest.json').write_text('{}', encoding='utf-8')
            (folder / 'reference.png').write_bytes(b'reference')
            entries = []
            for i in range(1, 6):
                identifier = f'PA{i:02d}'
                (folder / (identifier + '.ifc')).write_text(
                    'IFC mock only for ZIP structure', encoding='utf-8'
                )
                entries.append({'option': identifier})
            archive = folder.with_suffix('.zip')
            write_verified_archive(folder, archive, entries)
            with ZipFile(archive) as handle:
                self.assertEqual(len(handle.namelist()), 7)
                self.assertIsNone(handle.testzip())

    def test_missing_ifc_rejected_without_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / 'manifest.json').write_text('{}')
            (folder / 'reference.png').write_bytes(b'r')
            with self.assertRaises(ValueError):
                write_verified_archive(
                    folder, folder.with_suffix('.zip'), [{'option': 'PA01'}],
                )


if __name__ == '__main__':
    unittest.main()
