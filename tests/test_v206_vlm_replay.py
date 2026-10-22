import json
import tempfile
import unittest
from pathlib import Path
from evaluation.run_vlm_holdout import evaluate_jsonl


class V206VLMReplayTests(unittest.TestCase):
    def test_actual_holdout_records_evaluated_not_trained(self):
        fields = ('building_type', 'floor_count', 'roof_type', 'facade_system')
        item = {'project_id': 'held_out_206', 'split': 'test',
                'truth': dict.fromkeys(fields),
                'prediction': dict.fromkeys(fields),
                'inference_completed': True}
        item['truth']['floor_count'] = 3
        item['prediction']['floor_count'] = 3
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'holdout.jsonl'
            path.write_text(json.dumps(item) + '\n', encoding='utf-8')
            result = evaluate_jsonl(path)
            self.assertEqual(result['metrics']['floor_count']['accuracy_including_abstention'], 1)
            self.assertFalse(result['training_performed_during_evaluation'])
            path.write_text('{not_json}', encoding='utf-8')
            with self.assertRaises(ValueError):
                evaluate_jsonl(path)
