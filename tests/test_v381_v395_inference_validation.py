import math
import unittest
from app.inference_validation import validate_inference_parameters


class InferenceValidationTests(unittest.TestCase):
    def setUp(self):
        self.valid = {
            'count': 1, 'steps': 20, 'seed': 1,
            'strength': 0.5, 'guidance': 7.5,
            'scale': 1, 'sharpness': 0,
        }

    def test_valid_request(self):
        self.assertTrue(validate_inference_parameters(self.valid))

    def test_nonfinite_float_rejected(self):
        for key in ('strength', 'guidance', 'sharpness'):
            for value in (float('nan'), float('inf')):
                with self.subTest(key=key, value=value):
                    data = dict(self.valid, **{key: value})
                    with self.assertRaises(ValueError):
                        validate_inference_parameters(data)

    def test_invalid_count_and_seed(self):
        for changes in ({'count': 99}, {'seed': -1}, {'seed': 2**65},
                        {'steps': 3}, {'scale': 3}):
            with self.assertRaises(ValueError):
                validate_inference_parameters(dict(self.valid, **changes))


if __name__ == '__main__':
    unittest.main()
