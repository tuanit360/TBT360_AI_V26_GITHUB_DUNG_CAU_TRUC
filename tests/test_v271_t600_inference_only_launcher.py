"""Local Windows inference-only launcher: reuse trained LoRA, never retrain."""
import unittest
from pathlib import Path


class T600InferenceOnlyLauncherTests(unittest.TestCase):
    def test_no_training_and_provenance_verified(self):
        path = (
            Path(__file__).resolve().parents[1] /
            'RUN_T600_INFERENCE_ONLY_WINDOWS.bat'
        )
        data = path.read_text(encoding='utf-8')
        self.assertNotIn('training.run_lora', data)
        self.assertIn('training.verify_real_checkpoint', data)
        self.assertIn('training.smoke_diffusers_inference', data)
        self.assertIn('training.verify_inference_evidence', data)
        self.assertIn('--device cuda', data)
        self.assertIn('image_%IMAGE_RUN%.png', data)
        self.assertIn('evidence_%IMAGE_RUN%.json', data)
        self.assertGreaterEqual(data.count('if errorlevel 1 goto :fail'), 4)
        self.assertLess(
            data.index('training.verify_real_checkpoint'),
            data.index('training.smoke_diffusers_inference'),
        )


if __name__ == '__main__':
    unittest.main()
