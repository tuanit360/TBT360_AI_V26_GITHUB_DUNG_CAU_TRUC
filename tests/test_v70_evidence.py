import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from learning.project_evidence import evaluate_project_bundle, evaluate_checkpoint_trials, draft_promotion


class V70EvidenceTests(unittest.TestCase):
    def make_bundle(self, root):
        model = {'units':'m','entities':[{'id':'w1','type':'wall','bbox_m':[0,0,5,.2]}]}
        files = {'bim.json':json.dumps(model).encode(), 'floor.svg':b'<svg/>', 'render.png':b'not-real-image-fixture'}
        assets = []
        for name, kind in [('bim.json','bim_json'),('floor.svg','floorplan'),('render.png','render')]:
            (root/name).write_bytes(files[name])
            asset = {'asset_id':name, 'kind':kind,'path':name, 'sha256':hashlib.sha256(files[name]).hexdigest(),'verification':'concept'}
            if kind != 'bim_json':asset['canonical_asset_id']='bim.json'
            assets.append(asset)
        manifest={'schema_version':'tbt360-v70-project-evidence-v1','projects':[{'project_id':'office_1','assets':assets}]}
        (root/'manifest.json').write_text(json.dumps(manifest))
        return manifest

    def test_bundle(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname);self.make_bundle(root)
            result=evaluate_project_bundle(root/'manifest.json',root)
            self.assertEqual('PASS',result['status'])
            self.assertEqual(3,len(result['items']))

    def test_tampered_bytes_blocked(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname);self.make_bundle(root)
            (root/'floor.svg').write_bytes(b'<svg>tampered</svg>')
            self.assertEqual('BLOCKED',evaluate_project_bundle(root/'manifest.json',root)['status'])

    def test_missing_canonical_link_blocked(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname);manifest=self.make_bundle(root)
            manifest['projects'][0]['assets'][-1]['canonical_asset_id']='absent'
            (root/'manifest.json').write_text(json.dumps(manifest))
            self.assertEqual('BLOCKED',evaluate_project_bundle(root/'manifest.json',root)['status'])

    def test_checkpoint_gate_and_rollback_proposal(self):
        trials=[{'checkpoint':n,'project_id':p,'score':s} for n,scores in [('baseline',[.72,.69]),('better',[.78,.73])] for p,s in zip(('office_1','office_2'),scores)]
        result=evaluate_checkpoint_trials(trials)
        self.assertEqual('PROMOTION_RECOMMENDED',result['status'])
        request=draft_promotion(result,'a'*64,'b'*64)
        self.assertEqual('PENDING_HUMAN_APPROVAL',request['status'])
        self.assertEqual('a'*64,request['rollback_sha256'])

    def test_degradation_blocks(self):
        trials=[{'checkpoint':n,'project_id':p,'score':s} for n,scores in [('baseline',[.72,.69]),('risky',[.96,.50])] for p,s in zip(('office_1','office_2'),scores)]
        self.assertEqual('KEEP_BASELINE',evaluate_checkpoint_trials(trials)['status'])

    def test_incomplete_comparison_blocks(self):
        data=[{'checkpoint':'baseline','project_id':'a','score':.5},{'checkpoint':'baseline','project_id':'b','score':.5},{'checkpoint':'new','project_id':'a','score':.9}]
        self.assertEqual('BLOCKED',evaluate_checkpoint_trials(data)['status'])

if __name__ == '__main__': unittest.main()
