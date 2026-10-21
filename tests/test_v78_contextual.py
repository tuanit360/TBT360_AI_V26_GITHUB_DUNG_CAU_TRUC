import tempfile
import unittest
from pathlib import Path
import numpy as np
from recognition.contextual import contextual_features, _box_mean, fit, infer


class ContextualVisionTests(unittest.TestCase):
    def test_box_mean_on_constant(self):
        self.assertTrue(np.allclose(_box_mean(np.ones((20, 20)), 6), 1.0))

    def test_features_valid(self):
        self.assertEqual(contextual_features(np.zeros((30, 31), dtype=np.uint8)).shape, (930, 8))

    def test_train_infer_from_v77_demo(self):
        root = Path(__file__).resolve().parents[1]
        dataset = root / 'demo_data' / 'v77_synthetic'
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / 'weights.npz'
            report = fit(dataset, checkpoint, Path(directory) / 'report.json', epochs=12, patience=5)
            self.assertTrue(checkpoint.is_file())
            self.assertGreaterEqual(report['selected_epoch'], 1)
            self.assertIn('test', report['metrics'])
            result = infer(dataset / 'office_3.png', checkpoint, Path(directory) / 'prediction.png')
            self.assertTrue(Path(result['output']).exists())

    def test_bad_patience(self):
        with self.assertRaises(ValueError):
            fit('missing', 'weights.npz', 'report.json', epochs=3, patience=4)


if __name__ == '__main__':
    unittest.main()
