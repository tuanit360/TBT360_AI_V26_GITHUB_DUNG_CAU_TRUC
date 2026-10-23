"""Dataset split must reject visually duplicated projects before any LoRA training."""
import json
import random
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from PIL.PngImagePlugin import PngInfo

from tools.training_leakage_check import check_training_leakage


def make_image(seed):
    randomizer = random.Random(seed)
    image = Image.new('RGB', (80, 64))
    image.putdata([
        (randomizer.randrange(256), randomizer.randrange(256),
         randomizer.randrange(256))
        for _ in range(80 * 64)
    ])
    return image


class V271TrainingLeakageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.manifest = self.root / 'project_manifest.jsonl'
        self.rows = []
        for index, project in enumerate(('Project_A', 'Project_B', 'Project_C')):
            filename = f'{project}.png'
            make_image(index + 100).save(self.root / filename)
            self.rows.append({
                'project_id': project,
                'file_name': filename,
                'caption': f'Architectural office facade for {project}',
                'discipline': 'architecture',
                'verification': 'concept',
            })
        self.write_manifest()

    def tearDown(self):
        self.temporary.cleanup()

    def write_manifest(self):
        self.manifest.write_text(
            ''.join(json.dumps(row) + '\n' for row in self.rows),
            encoding='utf-8',
        )

    def test_distinct_projects_can_pass_without_claiming_training(self):
        report = check_training_leakage(self.manifest, self.root)
        self.assertEqual(report['status'], 'SPLIT_VALID_NOT_TRAINED')
        self.assertFalse(report['cross_split_pixel_duplicates'])

    def test_nonimage_manifest_record_blocks_training_gate(self):
        first = self.rows[0]
        first['file_name'] = 'notes.txt'
        (self.root / 'notes.txt').write_text('architectural annotations', encoding='utf-8')
        self.write_manifest()
        report = check_training_leakage(self.manifest, self.root)
        self.assertEqual(report['status'], 'BLOCKED')
        self.assertTrue(any(
            isinstance(error, dict)
            and error.get('reason') == 'Unsupported/non-image training file'
            for error in report['errors']
        ))

    def test_valid_dataset_reports_images_in_both_splits(self):
        report = check_training_leakage(self.manifest, self.root)
        self.assertEqual(report['status'], 'SPLIT_VALID_NOT_TRAINED')
        self.assertGreater(report['train_image_count'], 0)
        self.assertGreater(report['validation_image_count'], 0)

    def test_different_brightness_flat_images_not_false_duplicate(self):
        first = check_training_leakage(self.manifest, self.root)
        train_project = first['train_projects'][0]
        validation_project = first['validation_projects'][0]
        Image.new('RGB', (80, 64), (30, 30, 30)).save(
            self.root / f'{train_project}.png'
        )
        Image.new('RGB', (80, 64), (220, 220, 220)).save(
            self.root / f'{validation_project}.png'
        )
        report = check_training_leakage(self.manifest, self.root)
        self.assertEqual(report['status'], 'SPLIT_VALID_NOT_TRAINED')
        self.assertFalse(report['cross_split_near_duplicates'])

    def test_same_pixels_with_different_png_metadata_are_blocked(self):
        first = check_training_leakage(self.manifest, self.root)
        train_project = first['train_projects'][0]
        validation_project = first['validation_projects'][0]
        original = Image.open(self.root / f'{train_project}.png')
        changed_metadata = PngInfo()
        changed_metadata.add_text('export', 'different-application')
        original.save(self.root / f'{validation_project}.png',
                      pnginfo=changed_metadata)
        report = check_training_leakage(self.manifest, self.root)
        self.assertEqual(report['status'], 'BLOCKED')
        self.assertTrue(report['cross_split_pixel_duplicates'])


if __name__ == '__main__':
    unittest.main()
