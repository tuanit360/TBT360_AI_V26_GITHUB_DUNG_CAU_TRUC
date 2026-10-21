import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from training.gated_dataset import stage, verify


class CertifiedTrainingTests(unittest.TestCase):
    def fixture(self, root):
        rows = []
        for i in range(4):
            path = root / f'building_{i}.png'
            img = Image.new('RGB', (280, 280))
            pix = img.load()
            for y in range(280):
                for x in range(280):
                    pix[x, y] = ((x + i * 31) % 256, (y * (i + 1)) % 256, (x * y + i * 31) % 256)
            img.save(path)
            rows.append({'project_id': f'building_{i}', 'file_name': path.name,
                         'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                         'caption': f'Original architectural office tower exterior view {i}',
                         'discipline': 'architecture', 'verification': 'concept',
                         'label_classes': ['wall', 'window'], 'license': 'synthetic fixture',
                         'source': 'synthetic test-only', 'consent_to_train': True})
        manifest = root / 'manifest.jsonl'
        manifest.write_text(''.join(json.dumps(r) + '\n' for r in rows))
        return manifest

    def test_stage_train_validation_isolation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'raw'
            root.mkdir()
            manifest = self.fixture(root)
            destination = Path(temp) / 'certified'
            report = stage(manifest, root, destination)
            self.assertEqual(report['status'], 'PASS')
            self.assertGreater(report['validation_count'], 0)
            self.assertFalse(set(report['train_projects']) & set(report['validation_projects']))
            self.assertEqual(verify(destination)['status'], 'PASS')
            self.assertEqual(len(list((destination / 'prepared').glob('*.png'))), report['train_count'])
            self.assertEqual(len(list((destination / 'validation').glob('*.png'))), report['validation_count'])

    def test_modified_train_image_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'raw'; root.mkdir()
            dest = Path(temp) / 'certified'
            stage(self.fixture(root), root, dest)
            image = next((dest / 'prepared').glob('*.png'))
            image.write_bytes(b'bad')
            with self.assertRaises(ValueError):
                verify(dest)

    def test_modified_train_caption_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'raw'; root.mkdir()
            dest = Path(temp) / 'certified'
            stage(self.fixture(root), root, dest)
            metadata = dest / 'prepared' / 'metadata.jsonl'
            metadata.write_text(metadata.read_text().replace('Original', 'False'))
            with self.assertRaises(ValueError):
                verify(dest)

    def test_unapproved_extra_image_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'raw'; root.mkdir()
            dest = Path(temp) / 'certified'
            stage(self.fixture(root), root, dest)
            Image.new('RGB', (280, 280), 'red').save(dest / 'prepared' / 'unapproved.png')
            with self.assertRaises(ValueError):
                verify(dest)

    def test_refuse_existing_dataset_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'raw'; root.mkdir()
            dest = Path(temp) / 'certified'
            manifest = self.fixture(root)
            stage(manifest, root, dest)
            with self.assertRaises(FileExistsError):
                stage(manifest, root, dest)

    def test_no_consent_blocks_staging(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'raw'; root.mkdir()
            dest = Path(temp) / 'certified'
            manifest = self.fixture(root)
            lines = [json.loads(line) for line in manifest.read_text().splitlines()]
            lines[0]['consent_to_train'] = False
            manifest.write_text(''.join(json.dumps(line) + '\n' for line in lines))
            with self.assertRaises(ValueError):
                stage(manifest, root, dest)
            self.assertFalse(dest.exists())

if __name__ == '__main__':
    unittest.main()
