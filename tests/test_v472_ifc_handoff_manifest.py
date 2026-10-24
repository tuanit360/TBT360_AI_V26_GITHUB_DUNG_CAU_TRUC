import tempfile
import unittest
import hashlib
from pathlib import Path
from app.ifc_handoff_manifest import validate_handoff_manifest


class IFCCommonBuildingHandoffTests(unittest.TestCase):
    def test_five_options_share_envelope_but_have_distinct_deltas(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            options = []
            for i in range(1, 6):
                id = f'PA{i:02d}'
                content = f'IFC fixture {i}'.encode()
                (root / f'{id}.ifc').write_bytes(content)
                options.append({
                    'option': id, 'width_m': 9, 'length_m': 12,
                    'height_m': 3.3, 'shared_building_reference': 'ONE',
                    'variation': {'x': i}, 'engineering_verified': False,
                    'ifc_sha256': hashlib.sha256(content).hexdigest(),
                })
            payload = {
                'schema': 'bimai360.five_ifc_concept.v2',
                'alternatives_not_independent_houses': True,
                'image_exported': False, 'engineering_verified': False,
                'common_building_id': 'ONE', 'options': options,
            }
            self.assertTrue(validate_handoff_manifest(root, payload))
            payload['options'][4]['width_m'] = 10
            with self.assertRaisesRegex(ValueError, 'envelope'):
                validate_handoff_manifest(root, payload)

    def test_regression_no_second_manifest_overwrite(self):
        source = (Path(__file__).resolve().parents[1] /
                  'app' / 'five_concept_ifc.py').read_text(encoding='utf-8')
        self.assertEqual(source.count("manifest.write_text("), 1)
        self.assertIn('validate_handoff_manifest(destination, payload)', source)


if __name__ == '__main__':
    unittest.main()
