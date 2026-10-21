import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from learning.data_quality import inspect_training_manifest


class V71TrainingDataTests(unittest.TestCase):
    def make_set(self, folder, near=False):
        rows = []
        for i in range(4):
            path = folder / f'office_{i}.png'
            image = Image.new('RGB', (280, 280))
            for y in range(280):
                for x in range(280):
                    a = 0 if near else i * 31
                    image.putpixel((x, y), ((x + a) % 256, (y * (i + 1)) % 256, (x * y + a) % 256))
            image.save(path)
            rows.append({'project_id': f'office_{i}', 'file_name': path.name,
                         'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                         'caption': f'Office building {i} with detailed exterior geometry',
                         'discipline': 'architecture', 'verification': 'concept',
                         'label_classes': ['building', 'window'], 'license': 'test fixture',
                         'source': 'synthetic-test-only', 'consent_to_train': True})
        manifest = folder / 'dataset.jsonl'
        manifest.write_text('\n'.join(json.dumps(r) for r in rows), encoding='utf-8')
        return manifest, rows

    def test_good_grouped_split(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path, _ = self.make_set(root)
            report = inspect_training_manifest(path, root)
            self.assertEqual(report['status'], 'PASS', report['issues'])
            self.assertFalse(set(report['train_projects']) & set(report['validation_projects']))
            self.assertEqual(len(report['train_files']) + len(report['validation_files']), 4)

    def test_missing_training_permission_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path, rows = self.make_set(root)
            rows[0]['consent_to_train'] = False
            path.write_text('\n'.join(json.dumps(r) for r in rows))
            self.assertEqual(inspect_training_manifest(path, root)['status'], 'BLOCKED')

    def test_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path, rows = self.make_set(root)
            (root / rows[0]['file_name']).write_bytes(b'no longer a valid image')
            self.assertEqual(inspect_training_manifest(path, root)['status'], 'BLOCKED')

    def test_near_duplicate_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path, rows = self.make_set(root)
            # Copy identical visual content in a different PNG encoding.
            with Image.open(root / rows[0]['file_name']) as im:
                im.save(root / rows[1]['file_name'], optimize=True)
            rows[1]['sha256'] = hashlib.sha256((root / rows[1]['file_name']).read_bytes()).hexdigest()
            path.write_text('\n'.join(json.dumps(r) for r in rows))
            result = inspect_training_manifest(path, root)
            self.assertEqual(result['status'], 'BLOCKED')
            self.assertTrue(result['near_duplicate_pairs'])

    def test_path_escape_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path, rows = self.make_set(root)
            rows[0]['file_name'] = '../outside.png'
            path.write_text('\n'.join(json.dumps(r) for r in rows))
            self.assertEqual(inspect_training_manifest(path, root)['status'], 'BLOCKED')


if __name__ == '__main__':
    unittest.main()
