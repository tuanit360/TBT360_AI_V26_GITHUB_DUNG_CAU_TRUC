import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image

from app.canonical_bim_contract import build_handoff, save_handoff
from app.bim_handoff import export_handoff
from app.lora_validation import validate_adapter, verified_adapters


class V91HardeningTests(unittest.TestCase):
    def test_canonical_model_id_units_levels_and_views(self):
        project = build_handoff(
            'office_91', units='m',
            level_ids=[{'id': 'L01', 'elevation': 0.0}],
            elements=[{'id': 'W001', 'level_id': 'L01', 'category': 'wall',
                       'verification': 'concept'}],
        )
        self.assertEqual(project['bim_2d_projection_source'], 'canonical_entities_only')
        self.assertEqual(project['bim_3d_projection_source'], 'canonical_entities_only')
        self.assertFalse(project['ifc_export_ready'])
        with tempfile.TemporaryDirectory() as temp:
            path = save_handoff(temp, project)
            self.assertEqual(json.loads(path.read_text())['entities'][0]['id'], 'W001')

    def test_duplicate_and_orphan_entities_blocked(self):
        levels = [{'id': 'L01', 'elevation': 0}]
        wall = {'id': 'W01', 'level_id': 'L01', 'category': 'wall'}
        with self.assertRaises(ValueError):
            build_handoff('office_91', level_ids=levels, elements=[wall, wall])
        with self.assertRaises(ValueError):
            build_handoff('office_91', elements=[wall])

    def test_concept_export_includes_canonical_schema(self):
        with tempfile.TemporaryDirectory() as temp:
            export_handoff(Image.new('RGB', (300, 300), 'white'), temp,
                           prompt='Modern office', seed=42, project_id='office_91')
            data = json.loads((Path(temp) / 'canonical_bim_handoff.json').read_text())
            self.assertEqual(data['entities'], [])
            self.assertFalse(data['ifc_export_ready'])

    def test_lora_checksum_check_shared(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / 'architecture_v91'
            folder.mkdir()
            payload = b'test-weights-not-an-actual-model'
            (folder / 'pytorch_lora_weights.safetensors').write_bytes(payload)
            status = {'status': 'SUCCEEDED', 'weights_bytes': len(payload),
                      'weights_sha256': hashlib.sha256(payload).hexdigest()}
            (folder / 'training_status.json').write_text(json.dumps(status))
            self.assertTrue(validate_adapter(folder)['valid'])
            self.assertEqual(verified_adapters(temp), ['architecture_v91'])
            status['weights_sha256'] = 'bad'
            (folder / 'training_status.json').write_text(json.dumps(status))
            self.assertFalse(validate_adapter(folder)['valid'])
