import unittest
from PIL import Image
from app.advanced import validate_advanced, choose_size

class AdvancedTest(unittest.TestCase):
    def test_parameters(self):
        validate_advanced('SDXL 1.0',0.4,30,7,1)
        with self.assertRaises(ValueError): validate_advanced('unknown',0.4,30,7,1)
        with self.assertRaises(ValueError): validate_advanced('SD 1.5',0.99,30,7,1)
    def test_image_dimensions(self):
        w,h = choose_size('SD 1.5',Image.new('RGB',(1920,1080)))
        self.assertEqual(w%64,0)
        self.assertEqual(h%64,0)
        self.assertLessEqual(max(w,h),640)
