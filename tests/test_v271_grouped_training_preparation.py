"""Integration regression: metadata is never generated from leaking projects."""
import json
import random
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from tools.prepare_grouped_dataset import prepare


class GroupedPreparationTests(unittest.TestCase):
    def test_valid_projects_generate_train_only_metadata(self):
        with tempfile.TemporaryDirectory() as base:
            folder = Path(base) / 'prepared'
            folder.mkdir()
            rows = []
            for index, project in enumerate(('Office_A', 'Office_B', 'Office_C')):
                rng = random.Random(index + 37)
                image = Image.new('RGB', (80, 80))
                image.putdata([
                    (rng.randrange(256), rng.randrange(256), rng.randrange(256))
                    for _ in range(80 * 80)
                ])
                image.save(folder / f'{project}.png')
                rows.append({
                    'project_id': project,
                    'file_name': f'{project}.png',
                    'caption': f'Office architectural view {project}',
                    'discipline': 'architecture',
                    'verification': 'concept',
                })
            (folder / 'project_manifest.jsonl').write_text(
                ''.join(json.dumps(row) + '\n' for row in rows),
                encoding='utf-8',
            )
            audit = prepare(folder)
            entries = [
                json.loads(line)
                for line in (folder / 'metadata.jsonl').read_text(
                    encoding='utf-8'
                ).splitlines()
            ]
            self.assertEqual(len(entries), audit['train_images'])
            self.assertTrue((folder.parent / 'training_leakage_audit.json').exists())
            with self.assertRaises(FileExistsError):
                prepare(folder)

    def test_invalid_manifest_does_not_create_metadata(self):
        with tempfile.TemporaryDirectory() as base:
            folder = Path(base) / 'prepared'
            folder.mkdir()
            (folder / 'project_manifest.jsonl').write_text('', encoding='utf-8')
            with self.assertRaises(ValueError):
                prepare(folder)
            self.assertFalse((folder / 'metadata.jsonl').exists())


if __name__ == '__main__':
    unittest.main()
