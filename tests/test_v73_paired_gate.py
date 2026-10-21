import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from evaluation.paired_gate import evaluate


class PairedGateTests(unittest.TestCase):
    def fixture(self, root):
        def asset(name, white, mode='L'):
            path = root / name
            im = Image.new(mode, (8, 8), 0)
            for pos in white:
                im.putpixel(pos, 255 if mode == 'L' else (255, 255, 255))
            im.save(path)
            return {'path': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        reference_pixels = [(x,y) for x in range(2,6) for y in range(2,6)]
        ref = asset('reference.png', reference_pixels)
        orig = asset('input.png', [(0,0)], 'RGB')
        baseline_mask = asset('baseline_mask.png', reference_pixels[:8])
        candidate_mask = asset('candidate_mask.png', reference_pixels)
        baseline_img = asset('baseline.png', reference_pixels[:8], 'RGB')
        candidate_img = asset('candidate.png', reference_pixels, 'RGB')
        settings = {'steps': 20, 'width': 8, 'height': 8, 'cfg': 7}
        base = {'seed':42, 'prompt':'office building', 'negative_prompt':'', 'settings':settings,
                'input_sha256':orig['sha256'], 'image':baseline_img, 'geometry_mask':baseline_mask}
        cand = dict(base, image=candidate_img, geometry_mask=candidate_mask)
        cases = []
        for pid in ('office_A', 'office_B'):
            cases.append({'project_id': pid, 'case_id':'front', 'input_image':orig,
                          'reference_geometry_mask':ref, 'baseline':dict(base), 'candidate':dict(cand)})
        m = {'schema_version':'tbt360-v73-paired-geometry-v1', 'train_project_ids':['training_C'],
             'validation_project_ids':['office_A','office_B'], 'checkpoint_baseline_sha256':'a'*64,
             'checkpoint_candidate_sha256':'b'*64, 'cases':cases}
        path = root/'manifest.json'
        path.write_text(json.dumps(m))
        return path, m

    def test_improvement_only_proposes_review(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); path, _=self.fixture(root)
            report=evaluate(path,root)
            self.assertEqual(report['status'],'REVIEW_CANDIDATE')
            self.assertTrue(report['requires_human_approval'])
            self.assertEqual(len(report['projects']),2)

    def test_seed_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); path,manifest=self.fixture(root)
            manifest['cases'][0]['candidate']['seed']=43
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'Unpaired setting'): evaluate(path,root)

    def test_project_leakage_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); path,manifest=self.fixture(root)
            manifest['train_project_ids'].append('office_B')
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'overlapping'): evaluate(path,root)

    def test_checksum_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); path,_=self.fixture(root)
            (root/'candidate.png').write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'SHA256'): evaluate(path,root)

    def test_missing_project_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); path,manifest=self.fixture(root)
            manifest['cases'].pop()
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'Each holdout'): evaluate(path,root)

    def test_bad_mask_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); path,manifest=self.fixture(root)
            image=Image.new('L',(8,8),128)
            image.save(root/'candidate_mask.png')
            manifest['cases'][0]['candidate']['geometry_mask']['sha256']=hashlib.sha256((root/'candidate_mask.png').read_bytes()).hexdigest()
            manifest['cases'][1]['candidate']['geometry_mask']['sha256']=manifest['cases'][0]['candidate']['geometry_mask']['sha256']
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'black/white'): evaluate(path,root)

    def test_downgrade_keeps_baseline(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); path,manifest=self.fixture(root)
            for case in manifest['cases']:
                case['baseline']['image'],case['candidate']['image']=case['candidate']['image'],case['baseline']['image']
                case['baseline']['geometry_mask'],case['candidate']['geometry_mask']=case['candidate']['geometry_mask'],case['baseline']['geometry_mask']
            path.write_text(json.dumps(manifest))
            self.assertEqual(evaluate(path,root)['status'],'KEEP_BASELINE')

    def test_unsafe_asset_path_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); path,manifest=self.fixture(root)
            manifest['cases'][0]['input_image']['path']='../../somewhere.png'
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'Unsafe'): evaluate(path,root)

if __name__=='__main__': unittest.main()
