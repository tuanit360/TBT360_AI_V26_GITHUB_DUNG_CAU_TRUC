import tempfile
import unittest
import zipfile
from pathlib import Path
from app.generation_stage import write_generation_stage
from app.diagnostic_bundle import build_diagnostic_zip


class GenerationStageTests(unittest.TestCase):
    def test_stages_are_recorded_and_in_offline_diagnostics(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_generation_stage(root, 'INFERENCE', 'BEGIN image=1')
            write_generation_stage(root, 'INFERENCE', 'DONE image=1')
            log = (root / 'logs' / 'generation_stage.log').read_text()
            self.assertIn('BEGIN image=1', log)
            self.assertIn('DONE image=1', log)
            archive = build_diagnostic_zip(root)
            with zipfile.ZipFile(archive) as package:
                self.assertIn('logs/generation_stage.log', package.namelist())

    def test_invalid_stage_is_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            write_generation_stage(folder, 'secret', 'dont write')
            self.assertFalse((Path(folder) / 'logs').exists())


if __name__ == '__main__':
    unittest.main()
