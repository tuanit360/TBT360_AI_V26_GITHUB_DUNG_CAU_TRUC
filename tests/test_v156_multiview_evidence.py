import copy
import json
import unittest
from app.architecture_evidence import parse_vlm_observations
from app.architecture_multiview import reconcile_architecture_observations


def observation(project, fingerprint, floors):
    fields = {}
    for field in ('building_type', 'floor_count', 'roof_type', 'facade_system'):
        fields[field] = {'value': floors if field == 'floor_count' else None,
                         'evidence': 'Visible repeated floor lines' if field == 'floor_count' else '',
                         'uncertain': True}
    return {
        'project_id': project, 'image_pixels_sha256': fingerprint * 64,
        'model_inference_performed': True,
        'structured_observations': parse_vlm_observations(json.dumps({'observations': fields})),
    }


class V156MultiviewEvidenceTests(unittest.TestCase):
    def test_conflicting_floor_counts_are_visible(self):
        left = observation('office_156', 'a', 3)
        right = observation('office_156', 'b', 4)
        original = copy.deepcopy(left)
        result = reconcile_architecture_observations([left, right])
        self.assertEqual(result['hypotheses']['floor_count']['status'], 'conflict')
        self.assertFalse(result['geometry_verified'])
        self.assertFalse(result['ifc_export_ready'])
        self.assertEqual(left, original)

    def test_duplicate_frame_does_not_increase_evidence(self):
        source = observation('office_156', 'a', 3)
        result = reconcile_architecture_observations([source, copy.deepcopy(source)])
        self.assertEqual(result['distinct_image_count'], 1)
        self.assertEqual(len(result['hypotheses']['floor_count']['candidate_observations']), 1)

    def test_project_boundary_enforced(self):
        with self.assertRaises(ValueError):
            reconcile_architecture_observations([
                observation('office_156', 'a', 3),
                observation('other_156', 'b', 3),
            ])
