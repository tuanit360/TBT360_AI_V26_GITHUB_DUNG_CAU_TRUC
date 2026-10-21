import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from evaluation.metric_gate import evaluate, _geometry_error

ROOT = Path(__file__).resolve().parents[1] / 'demo_data' / 'v75_metric'

class TestV75MetricGate(unittest.TestCase):
    def test_two_project_demo(self):
        result = evaluate(ROOT/'manifest.json', ROOT)
        self.assertEqual(result['status'], 'METRIC_GATE_PASS')
        self.assertEqual(len(result['projects']), 2)
    def test_tolerance_reject(self):
        result = evaluate(ROOT/'manifest.json', ROOT, 0.001)
        self.assertEqual(result['status'], 'METRIC_GATE_FAIL')
    def test_train_leak_reject(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = json.loads((ROOT/'manifest.json').read_text())
            m['train_project_ids']=['office_1']
            manifest = Path(tmp)/'manifest.json'
            manifest.write_text(json.dumps(m))
            with self.assertRaises(ValueError):
                evaluate(manifest, ROOT)
    def test_tampering_reject(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = json.loads((ROOT/'manifest.json').read_text())
            m['cases'][0]['predicted_bim']['sha256']='0'*64
            manifest = Path(tmp)/'manifest.json'
            manifest.write_text(json.dumps(m))
            with self.assertRaises(ValueError):
                evaluate(manifest, ROOT)
    def test_missing_entity_reject(self):
        m=json.loads((ROOT/'office_1_model.json').read_text())
        a=json.loads((ROOT/'office_1_annotation.json').read_text())
        a['entities'].pop()
        with self.assertRaises(ValueError):
            _geometry_error(m,a)
    def test_wrong_host_reject(self):
        m=json.loads((ROOT/'office_1_model.json').read_text())
        a=json.loads((ROOT/'office_1_annotation.json').read_text())
        next(e for e in a['entities'] if e['type']=='door')['host_id']='wall_B'
        with self.assertRaises(ValueError):
            _geometry_error(m,a)
