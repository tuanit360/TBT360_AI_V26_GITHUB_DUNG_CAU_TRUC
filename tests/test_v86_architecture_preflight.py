import unittest
from PIL import Image
from app.architecture_preflight import inspect_reference, cpu_generation_recommendation


class V86ArchitecturePreflightTests(unittest.TestCase):
    def test_missing_or_small_image_blocks(self):
        self.assertFalse(inspect_reference(None)['ready'])
        self.assertFalse(inspect_reference(Image.new('RGB', (100, 100)))['ready'])

    def test_normal_image_does_not_claim_bim_detection(self):
        result = inspect_reference(Image.new('RGB', (512, 512), 'gray'))
        self.assertTrue(result['ready'])
        self.assertFalse(result['collage_detection_verified'])

    def test_wide_reference_flagged_and_cpu_advice(self):
        result = inspect_reference(Image.new('RGB', (1400, 350), 'white'))
        self.assertTrue(any('board' in text for text in result['warnings']))
        self.assertEqual(len(cpu_generation_recommendation(False, 40, 4, 2)), 3)
        self.assertEqual(cpu_generation_recommendation(True, 40, 4, 2), [])
