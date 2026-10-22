import unittest
from evaluation.vlm_architecture_holdout import evaluate_predictions

FIELDS = ('building_type', 'floor_count', 'roof_type', 'facade_system')


def record(project, floor_truth, floor_prediction):
    truth = dict.fromkeys(FIELDS)
    truth['floor_count'] = floor_truth
    predicted = dict.fromkeys(FIELDS)
    predicted['floor_count'] = floor_prediction
    return {'project_id': project, 'split': 'test', 'truth': truth,
            'prediction': predicted, 'inference_completed': True}


class V201HoldoutTests(unittest.TestCase):
    def test_accuracy_distinguishes_error_and_abstention(self):
        report = evaluate_predictions([
            record('one', 3, 3), record('two', 4, None), record('three', 5, 4)])
        floor = report['metrics']['floor_count']
        self.assertEqual((floor['correct'], floor['incorrect'], floor['abstained']), (1, 1, 1))
        self.assertAlmostEqual(floor['coverage'], 2 / 3, places=5)
        self.assertFalse(report['architecture_model_trained_here'])

    def test_duplicate_or_uninferred_examples_are_rejected(self):
        a = record('one', 3, 3)
        with self.assertRaises(ValueError):
            evaluate_predictions([a, a])
        with self.assertRaises(ValueError):
            evaluate_predictions([dict(a, inference_completed=False)])
        with self.assertRaises(ValueError):
            evaluate_predictions([dict(a, split='train')])
