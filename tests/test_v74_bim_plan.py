import json
import tempfile
import unittest
from pathlib import Path
from evaluation.bim_plan import validate_model, render_plan, evaluate_plan

MODEL = {'units':'m','entities':[
    {'id':'w','type':'wall','bbox_m':[0,0,8,.3],'level_m':0},
    {'id':'d','type':'door','host_id':'w','bbox_m':[2,0,3,.3],'level_m':0},
    {'id':'win','type':'window','host_id':'w','bbox_m':[4,0,5,.3],'level_m':0},
]}

class V74BimPlanTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(len(validate_model(MODEL)),3)
    def test_invalid_host(self):
        m=json.loads(json.dumps(MODEL)); m['entities'][1]['host_id']='unknown'
        with self.assertRaisesRegex(ValueError,'host'): validate_model(m)
    def test_outside_host(self):
        m=json.loads(json.dumps(MODEL)); m['entities'][1]['bbox_m']=[9,0,10,.3]
        with self.assertRaisesRegex(ValueError,'outside'): validate_model(m)
    def test_duplicate_ids(self):
        m=json.loads(json.dumps(MODEL)); m['entities'][1]['id']='w'
        with self.assertRaisesRegex(ValueError,'duplicate'): validate_model(m)
    def test_invalid_units(self):
        m=dict(MODEL,units='mm')
        with self.assertRaisesRegex(ValueError,'metric'): validate_model(m)
    def test_bounded_render(self):
        mask=render_plan(MODEL,[0,0,10,10],100,100,'wall')
        self.assertEqual(mask.size,(100,100))
        self.assertGreater(sum(p==255 for p in mask.getdata()),0)
    def test_independent_annotation_comparison(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); f=root/'bim.json'; f.write_text(json.dumps(MODEL))
            render_plan(MODEL,[0,0,10,10],100,100,'wall').save(root/'wall_annotated.png')
            result=evaluate_plan(f,root,[0,0,10,10],100,100,['wall'],root/'results.json')
            self.assertEqual(result['scores']['wall']['plan_iou'],1)
            self.assertEqual(result['status'],'MEASUREMENT_ONLY')
    def test_missing_annotation_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); f=root/'bim.json';f.write_text(json.dumps(MODEL))
            with self.assertRaisesRegex(ValueError,'Missing independent'): evaluate_plan(f,root,[0,0,10,10],100,100,['wall'],root/'result.json')
