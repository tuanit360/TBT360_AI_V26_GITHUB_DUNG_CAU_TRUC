import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
from recognition.learned import load_manifest,train,infer

class LearnedTests(unittest.TestCase):
    def fixture(self,folder):
        rows=[]
        for idx,split in enumerate(('train','validation','test')):
            canvas=np.zeros((24,24),dtype=np.uint8); canvas[4:10,5:18]=220
            mask=np.zeros_like(canvas);mask[4:10,5:18]=1
            # Different patterns per project, deterministic and never identical
            canvas[12+idx,2:7]=80
            image=f'{split}.png';mask_name=f'{split}_mask.png'
            Image.fromarray(canvas).save(folder/image)
            Image.fromarray(mask).save(folder/mask_name)
            rows.append({'project_id':f'office_{idx}', 'split':split,'image':image,'mask':mask_name,
                'image_sha256':hashlib.sha256((folder/image).read_bytes()).hexdigest(),
                'label_status':'annotated','usage_allowed':True})
        (folder/'manifest.json').write_text(json.dumps({'samples':rows}))
        return rows
    def test_training_creates_real_weights_and_holdout_scores(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td); self.fixture(folder)
            result=train(folder,folder/'weights.npz',epochs=80)
            self.assertTrue((folder/'weights.npz').is_file())
            self.assertIn('test',result['metrics'])
            prediction=infer(folder/'test.png',folder/'weights.npz',folder/'pred.png')
            self.assertEqual(Image.open(prediction['mask']).size,(24,24))
    def test_leakage_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td);rows=self.fixture(folder)
            rows[1]['project_id']=rows[0]['project_id']
            (folder/'manifest.json').write_text(json.dumps({'samples':rows}))
            with self.assertRaises(ValueError):load_manifest(folder)
    def test_tampering_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td);self.fixture(folder)
            (folder/'train.png').write_bytes(b'corrupt')
            with self.assertRaises(Exception):load_manifest(folder)
    def test_no_rights_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td);rows=self.fixture(folder)
            rows[0]['usage_allowed']=False
            (folder/'manifest.json').write_text(json.dumps({'samples':rows}))
            with self.assertRaises(ValueError):load_manifest(folder)
