import json
import tempfile
import unittest
from pathlib import Path
from app.schematic_architecture import create_schematic
from evaluation.image_to_bim_benchmark import score_bim_prediction, evaluation_gate
from training.verify_real_checkpoint import verify_checkpoint


class V191TrainingGateTests(unittest.TestCase):
    def test_missing_and_forged_checkpoint_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            with self.assertRaises(ValueError):
                verify_checkpoint(folder)
            (folder / 'training_status.json').write_text(json.dumps(
                {'status':'SUCCEEDED','steps':300,'weights_sha256':'fake'}))
            (folder / 'pytorch_lora_weights.safetensors').write_bytes(b'not a checkpoint')
            with self.assertRaises(ValueError):
                verify_checkpoint(folder)

    def test_prediction_benchmark_is_not_a_training_claim(self):
        reference = create_schematic('reference_191', 12, 9, 3.2, 2)
        score = score_bim_prediction(reference, reference)
        self.assertEqual(score['category_f1'], 1)
        self.assertFalse(score['geometry_accuracy_evaluated'])
        score['reference_is_training_data'] = False
        with self.assertRaises(ValueError):
            evaluation_gate([score])
        other = []
        for project in ('reference_191','test_2','test_3'):
            item = dict(score, project_id=project)
            other.append(item)
        result = evaluation_gate(other)
        self.assertTrue(result['meets_category_f1_0_8'])
        self.assertFalse(result['model_is_trained'])
