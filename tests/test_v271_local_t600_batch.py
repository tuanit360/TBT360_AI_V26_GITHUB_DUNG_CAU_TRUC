"""Guard the local Windows T600 workflow stages and failure gates."""
import unittest
from pathlib import Path


class LocalT600BatchTests(unittest.TestCase):
    def test_real_workflow_requires_all_stages_and_failure_checks(self):
        root = Path(__file__).resolve().parents[1]
        content = (root / 'RUN_REAL_T600_LOCAL_WINDOWS.bat').read_text(
            encoding='utf-8',
        )
        stages = (
            'training.local_hardware_diagnostic',
            'training.preflight_real_gpu',
            'training.run_lora',
            'training.verify_real_checkpoint',
            'training.smoke_diffusers_inference',
            'training.verify_inference_evidence',
        )
        offsets = [content.index(stage) for stage in stages]
        self.assertEqual(offsets, sorted(offsets))
        self.assertGreaterEqual(content.count('if errorlevel 1 goto :fail'), 6)
        self.assertIn('exit /b 1', content)
        self.assertIn('--device cuda', content)
        self.assertNotIn('%~1', content)


if __name__ == '__main__':
    unittest.main()
