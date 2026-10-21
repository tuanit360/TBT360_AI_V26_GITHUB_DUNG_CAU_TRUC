import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from recognition.raster import propose,compare,components
ROOT=Path(__file__).resolve().parents[1]/'demo_data'/'v76_raster'
class RecognitionTest(unittest.TestCase):
    def test_demo_proposals_match_synthetic_reference(self):
        actual=propose(ROOT/'plan.png',[0,0,10,10]);expected=json.loads((ROOT/'reference.json').read_text())
        self.assertTrue(compare(actual,expected)['passed']);self.assertEqual(len(actual['entities']),2)
    def test_wrong_bounds_fails(self):
        with self.assertRaises(ValueError):propose(ROOT/'plan.png',[0,0,0,10])
    def test_wrong_class_fails(self):
        with self.assertRaises(ValueError):propose(ROOT/'plan.png',[0,0,10,10],'door')
    def test_mask_noise_is_filtered(self):
        im=Image.new('L',(20,20),0);im.putpixel((1,1),255)
        self.assertEqual(components(im),[])
    def test_connected_blob_merges(self):
        im=Image.new('L',(20,20),0)
        for x in range(2,9): im.putpixel((x,5),255)
        for y in range(5,12): im.putpixel((8,y),255)
        self.assertEqual(len(components(im)),1)
    def test_extra_detection_fails(self):
        actual=propose(ROOT/'plan.png',[0,0,10,10]);expected=json.loads((ROOT/'reference.json').read_text())
        expected['entities'].pop()
        self.assertFalse(compare(actual,expected)['passed'])
    def test_corrupt_image_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'broken.png';p.write_bytes(b'bad')
            with self.assertRaises(Exception):propose(p,[0,0,10,10])
