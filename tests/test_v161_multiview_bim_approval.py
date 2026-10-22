import copy
import json
import unittest
from app.architecture_evidence import parse_vlm_observations
from app.architecture_multiview import reconcile_architecture_observations
from app.multiview_bim_approval import approve_multiview_concept


def observation(digest, floors):
    data = {}
    for key in ('building_type', 'floor_count', 'roof_type', 'facade_system'):
        value = floors if key == 'floor_count' else None
        data[key] = {'value': value, 'evidence': 'Visible facade levels' if value else '',
                     'uncertain': True}
    return {
        'project_id': 'office_161', 'image_pixels_sha256': digest * 64,
        'model_inference_performed': True,
        'structured_observations': parse_vlm_observations(json.dumps({'observations': data})),
    }


class V161BIMApprovalTests(unittest.TestCase):
    def setUp(self):
        self.views = [observation('a', 3), observation('b', 4)]
        self.report = reconcile_architecture_observations(self.views)
        self.dimensions = {'width_m': 12, 'depth_m': 8, 'floor_height_m': 3.2,
                           'floor_count': 3, 'user_approved': True}

    def test_conflict_requires_explicit_acknowledgement(self):
        with self.assertRaises(ValueError):
            approve_multiview_concept(self.views, self.report, self.dimensions)
        original = copy.deepcopy(self.views)
        model = approve_multiview_concept(self.views, self.report, self.dimensions, True)
        self.assertEqual(self.views, original)
        self.assertFalse(model['ifc_export_ready'])
        self.assertEqual(model['concept_source']['multiview_conflict_fields'], ['floor_count'])
        self.assertEqual(len(model['concept_source']['observation_image_sha256_list']), 2)

    def test_tampered_consensus_rejected(self):
        tampered = copy.deepcopy(self.report)
        tampered['hypotheses']['floor_count']['status'] = 'unverified_agreement'
        with self.assertRaises(ValueError):
            approve_multiview_concept(self.views, tampered, self.dimensions, True)

    def test_missing_user_approval_rejected(self):
        with self.assertRaises(ValueError):
            approve_multiview_concept(self.views, self.report,
                                      dict(self.dimensions, user_approved=False), True)

    def test_non_conflicting_floor_mismatch_requires_acknowledgement(self):
        views = [observation('a', 4), observation('b', 4)]
        report = reconcile_architecture_observations(views)
        with self.assertRaises(ValueError):
            approve_multiview_concept(views, report, self.dimensions)
