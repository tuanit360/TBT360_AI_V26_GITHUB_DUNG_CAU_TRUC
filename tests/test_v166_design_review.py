import copy
import json
import unittest
from app.architecture_evidence import parse_vlm_observations
from app.architecture_design_review import (
    create_reviewed_architecture_proposal, verify_reviewed_proposal)


def sample(fingerprint, floors):
    observations = {
        key: {'value': floors if key == 'floor_count' else None,
              'evidence': 'Window rows' if key == 'floor_count' else '',
              'uncertain': True}
        for key in ('building_type', 'floor_count', 'roof_type', 'facade_system')
    }
    return {'project_id': 'office_166', 'image_pixels_sha256': fingerprint * 64,
            'model_inference_performed': True,
            'structured_observations': parse_vlm_observations(
                json.dumps({'observations': observations}))}


class V166ArchitectureReviewTests(unittest.TestCase):
    def setUp(self):
        self.views = [sample('a', 3), sample('b', 3)]
        self.constraints = {'width_m': 12, 'depth_m': 8, 'floor_height_m': 3.2,
                            'floor_count': 3, 'user_approved': True}

    def test_roundtrip_advisory_does_not_change_geometry(self):
        model, review = create_reviewed_architecture_proposal(self.views, self.constraints)
        self.assertEqual(len(model['entities']), 12)
        self.assertFalse(model['design_evidence_review']['advisory_hypotheses']['floor_count']['use_for_geometry'])
        self.assertEqual(verify_reviewed_proposal(model, self.views, self.constraints)['source_images'], 2)

    def test_tampering_detected(self):
        model, _ = create_reviewed_architecture_proposal(self.views, self.constraints)
        edited = copy.deepcopy(model)
        edited['entities'][0]['geometry']['origin'][0] = 99
        with self.assertRaises(ValueError):
            verify_reviewed_proposal(edited, self.views, self.constraints)

    def test_user_approval_required(self):
        with self.assertRaises(ValueError):
            create_reviewed_architecture_proposal(
                self.views, dict(self.constraints, user_approved=False))
