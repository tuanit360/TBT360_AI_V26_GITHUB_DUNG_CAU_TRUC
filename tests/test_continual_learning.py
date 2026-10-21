import json
import tempfile
import unittest
from pathlib import Path
from learning.core import (dataset_audit, validate_bim, geometry_score, select_checkpoint, compare_runs, append_feedback)

class LearningTests(unittest.TestCase):
    def test_group_splits(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); items=[]
            for project in ('office_a','office_b','office_c','office_d'):
                for i in range(2):
                    filename=f'{project}_{i}.png'; (root/filename).write_bytes(f'{project}:{i}'.encode())
                    items.append({'project_id':project,'file_name':filename,'caption':'office facade with fenestration','discipline':'architecture','verification':'concept'})
            manifest=root/'labels.jsonl';manifest.write_text(''.join(json.dumps(x)+'\n' for x in items))
            result=dataset_audit(manifest,root)
            self.assertEqual('PASS',result['status'])
            self.assertFalse(set(result['train_projects']) & set(result['validation_projects']))
            self.assertEqual(8,result['train_images']+result['validation_images'])
    def test_duplicate_image_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); rows=[]
            for project in ('office_a','office_b','office_c'):
                filename=project+'.png';(root/filename).write_bytes(b'identical')
                rows.append({'project_id':project,'file_name':filename,'caption':'office model ground truth','discipline':'bim','verification':'concept'})
            manifest=root/'labels.jsonl';manifest.write_text(''.join(json.dumps(x)+'\n' for x in rows))
            self.assertEqual('BLOCKED',dataset_audit(manifest,root)['status'])
    def test_geometry_checks(self):
        base={'units':'m','entities':[{'id':'w','type':'wall','bbox_m':[0,0,5,.2]},{'id':'d','type':'door','bbox_m':[1,0,1.9,.2],'host_id':'w'}]}
        self.assertEqual('PASS',validate_bim(base)['status'])
        invalid=json.loads(json.dumps(base));invalid['entities'][1]['host_id']='missing'
        self.assertEqual('BLOCKED',validate_bim(invalid)['status'])
        self.assertEqual(0,geometry_score(base,base)['mean_bbox_coordinate_error_m'])
    def test_checkpoint_overfit(self):
        records=[{'checkpoint':'overfit','train_score':.99,'validation_score':.50},{'checkpoint':'safe','train_score':.83,'validation_score':.80}]
        result=select_checkpoint(records)
        self.assertEqual('safe',result['selected'])
        self.assertEqual('overfit',result['rejected'][0]['checkpoint'])
    def test_same_seed_required(self):
        original={'model_input_sha256':'x','seed':42,'prompt':'office','resolution':[512,512],'control_input_sha256':'y'}
        self.assertEqual('COMPARABLE',compare_runs(original,dict(original))['status'])
        self.assertEqual('BLOCKED',compare_runs(original,{**original,'seed':43})['status'])
    def test_opt_in_feedback(self):
        with tempfile.TemporaryDirectory() as d:
            feedback={'output_sha256':'f'*64,'project_id':'office_a','rating':5,'comment':'ok','consent':False}
            with self.assertRaises(ValueError):append_feedback(Path(d)/'queue.jsonl',feedback)
            feedback['consent']=True
            self.assertEqual('PENDING_HUMAN_REVIEW',append_feedback(Path(d)/'queue.jsonl',feedback)['status'])

if __name__=='__main__': unittest.main()
