import json
import unittest
from app.architecture_evidence import (
    parse_vlm_observations, approve_schematic_from_vlm,
)


def response():
    return {'observations': {
        'building_type': {'value': 'office', 'evidence': 'visible facade', 'uncertain': True},
        'floor_count': {'value': 3, 'evidence': 'three rows of windows', 'uncertain': True},
        'roof_type': {'value': None, 'evidence': '', 'uncertain': True},
        'facade_system': {'value': 'glass', 'evidence': 'large glazed panels', 'uncertain': True},
    }}


class V151ArchitectureEvidenceTests(unittest.TestCase):
    def test_strict_structured_observation(self):
        data = parse_vlm_observations(json.dumps(response()))
        self.assertEqual(data['floor_count']['value'], 3)
        self.assertFalse(data['floor_count']['verified'])
        self.assertIsNone(data['roof_type']['value'])

    def test_invalid_json_and_ungrounded_claims_fail_closed(self):
        with self.assertRaises(ValueError):
            parse_vlm_observations('three floors, certain')
        data = response()
        data['observations']['floor_count']['evidence'] = ''
        with self.assertRaises(ValueError):
            parse_vlm_observations(json.dumps(data))
        data = response()
        data['observations']['floor_count']['value'] = 3.5
        with self.assertRaises(ValueError):
            parse_vlm_observations(json.dumps(data))

    def test_approved_constraints_produce_concept_not_inferred_bim(self):
        observation = {'model_inference_performed': True, 'project_id': 'office_151',
                       'image_pixels_sha256': 'abcdef',
                       'structured_observations': parse_vlm_observations(json.dumps(response()))}
        dimensions = {'width_m': 12, 'depth_m': 8, 'floor_height_m': 3.2,
                      'floor_count': 3, 'user_approved': True}
        with self.assertRaises(ValueError):
            approve_schematic_from_vlm(observation, dict(dimensions, user_approved=False))
        model = approve_schematic_from_vlm(observation, dimensions)
        self.assertEqual(len(model['entities']), 12)
        self.assertFalse(model['ifc_export_ready'])
        self.assertFalse(model['concept_source']['derived_dimensions_from_image'])
