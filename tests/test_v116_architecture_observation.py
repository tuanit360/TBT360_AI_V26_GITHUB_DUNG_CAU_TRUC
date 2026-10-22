import unittest
from PIL import Image
from app.architecture_observation import inspect_architecture, combine_project_observations


class ArchitectureObservationTests(unittest.TestCase):
    def test_single_image_is_unverified_without_ml_model(self):
        report = inspect_architecture(Image.new('RGB', (512, 384), 'white'), 'office_116')
        self.assertFalse(report['model_inference_performed'])
        self.assertIsNone(report['architecture_hypotheses']['floor_count'])
        self.assertEqual(report['bim_entities'], [])

    def test_multiview_requires_same_project(self):
        image = Image.new('RGB', (512, 384), 'white')
        first = inspect_architecture(image, 'office_116')
        second = inspect_architecture(image, 'office_116')
        result = combine_project_observations([first, second])
        self.assertEqual(result['view_count'], 1)
        self.assertFalse(result['bim_export_ready'])
        different = inspect_architecture(image, 'other_116')
        with self.assertRaises(ValueError):
            combine_project_observations([first, different])

    def test_reject_invalid_reference(self):
        with self.assertRaises(ValueError):
            inspect_architecture(Image.new('RGB', (100, 100)), 'office_116')
