import tempfile
import unittest
from pathlib import Path
from PIL import Image
from tbt360_ai.engine import list_images, split_items, run_training, predict_image


class TestEngine(unittest.TestCase):
    def test_validation_and_split(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name, color in [('school', (230, 60, 60)), ('office', (60, 60, 230))]:
                (root / name).mkdir()
                for i in range(5):
                    Image.new('RGB', (40, 40), color).save(root/name/f'{i}.png')
            labels, items = list_images(root)
            train, valid = split_items(labels, items)
            self.assertEqual(len(labels), 2)
            self.assertEqual(len(train) + len(valid), 10)
            self.assertEqual(set(x[0] for x in train) & set(x[0] for x in valid), set())

    def test_one_epoch_and_predict(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'dataset'
            for name, color in [('school', (230, 60, 60)), ('office', (60, 60, 230))]:
                (root / name).mkdir(parents=True)
                for i in range(4):
                    Image.new('RGB', (48, 48), color).save(root/name/f'{i}.png')
            out = Path(d) / 'output'
            result = run_training(root, out, epochs=1, batch_size=2)
            self.assertTrue((out/'best.pt').exists())
            self.assertTrue((out/'metrics.csv').exists())
            predicted = predict_image(out/'best.pt', root/'school'/'0.png')
            self.assertEqual(len(predicted), 2)
            self.assertEqual(result['total_images'], 8)


if __name__ == '__main__':
    unittest.main()
