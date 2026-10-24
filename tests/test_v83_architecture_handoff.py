import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from app.architecture_crop import propose_crops, export_crop_review
from app.bim_handoff import build_prompt, export_handoff


class V83ArchitectureHandoffTests(unittest.TestCase):
    def test_board_proposals_are_review_only(self):
        image = Image.new('RGB', (600, 400), '#abcabc')
        crops = propose_crops(image, 2, 3)
        self.assertEqual(len(crops), 6)
        self.assertTrue(all(item['review_status'] == 'NEEDS_REVIEW' for item in crops))
        with self.assertRaises(ValueError):
            propose_crops(image, 9, 1)

    def test_export_is_concept_not_verified_bim(self):
        image = Image.new('RGB', (320, 300), 'white')
        with tempfile.TemporaryDirectory() as tmp:
            report = export_handoff(
                image, Path(tmp) / 'handoff', prompt='Office with flat roof',
                seed=42, project_id='office_83', floors_hint=5
            )
            self.assertFalse(report['geometry_validated'])
            self.assertFalse(report['engineering_verified'])
            self.assertEqual(report['units'], 'pixels_only_no_real_world_scale')
            self.assertTrue((Path(tmp) / 'handoff' / 'concept_reference.png').is_file())

    def test_prompt_and_review_manifest(self):
        self.assertIn('5-story', build_prompt('office', 5, 'glass', 'flat roof', 'corner', 'daylight', 'steel'))
        with tempfile.TemporaryDirectory() as tmp:
            _, records = export_crop_review(Image.new('RGB', (400, 400)), 2, 2, tmp)
            self.assertEqual(len(records), 4)
            self.assertEqual(json.loads((Path(tmp) / 'review.json').read_text())['schema'],
                             'tbt360.crop_review.v83')
