"""Protect the real GPU training contract from accidental mock-only success."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'gpu-train.yml'


class RealGPUWorkflowContractTests(unittest.TestCase):
    def test_requires_real_trained_checkpoint_inference_and_evidence(self):
        source = WORKFLOW.read_text(encoding='utf-8')
        self.assertIn('runs-on: [self-hosted, linux, x64, bimai360-gpu]', source)
        self.assertIn('python -m training.run_lora', source)
        self.assertIn('python -m training.verify_real_checkpoint', source)
        self.assertIn('python -m training.smoke_diffusers_inference', source)
        self.assertIn('--adapter "loras/$RUN_NAME"', source)
        self.assertIn('--device cuda', source)
        self.assertIn('python -m training.verify_inference_evidence', source)
        self.assertIn('bimai360-gpu-inference-evidence-', source)
        self.assertLess(
            source.index('python -m training.run_lora'),
            source.index('python -m training.smoke_diffusers_inference'),
        )
        self.assertLess(
            source.index('python -m training.smoke_diffusers_inference'),
            source.index('python -m training.verify_inference_evidence'),
        )
        self.assertLess(
            source.index('python -m training.verify_inference_evidence'),
            source.index('Upload checkpoint and provenance if complete'),
        )


if __name__ == '__main__':
    unittest.main()
