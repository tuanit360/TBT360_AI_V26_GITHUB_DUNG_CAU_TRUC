"""Regression: online image generation must not require a local SD1.5 folder."""
import unittest
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

from app.image_generation_contract import image_generation_contract


class V271OnlineModelFallbackTests(unittest.TestCase):
    def test_online_path_invokes_generator_without_local_sd15(self):
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / 'generated.png'
            image_path.write_bytes(b'fake-image-fixture')
            archive_path = Path(directory) / 'output.zip'
            with zipfile.ZipFile(archive_path, 'w') as bundle:
                bundle.write(image_path, arcname=image_path.name)
            with patch('app.local_workspace.record_operation'), patch(
                'app.image_generation_contract.render_image_gallery',
                return_value='<p>generated</p>',
            ):
                calls = []
                def generate(*arguments, **kwargs):
                    calls.append(True)
                    return [(str(image_path), 'test')], str(archive_path), 'OK'
                result = image_generation_contract(
                    Path('.'), generate, (),
                    offline=False, readiness={'model_files_complete': False},
                )
        self.assertEqual(len(calls), 1)
        self.assertEqual(result[0], '<p>generated</p>')
        self.assertEqual(result[1], str(archive_path))
        self.assertIn('PASS', result[3])

    def test_ui_routes_through_shared_contract(self):
        source = (Path(__file__).resolve().parents[1] /
                  'app' / 'generate.py').read_text(encoding='utf-8')
        self.assertIn("offline = os.environ.get('TBT360_OFFLINE') == '1'", source)
        self.assertIn('readiness = inspect_local_assets(ROOT) if offline else None', source)
        self.assertIn('image_generation_contract(', source)


if __name__ == '__main__':
    unittest.main()
