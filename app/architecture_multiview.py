"""V152–V156 evidence-aware multimodal observation consensus.

No model output is considered ground truth. Different images may disagree;
conflicts remain visible and cannot silently mutate canonical BIM.
"""
from collections import defaultdict

from app.architecture_evidence import FIELDS


def reconcile_architecture_observations(observations):
    if not isinstance(observations, list) or not observations:
        raise ValueError('At least one observation required')
    project = observations[0].get('project_id')
    seen = set()
    grouped = defaultdict(list)
    for observation in observations:
        if observation.get('project_id') != project:
            raise ValueError('Mixed-project observations forbidden')
        if observation.get('model_inference_performed') is not True:
            raise ValueError('Uninferred image cannot be used for AI consensus')
        digest = observation.get('image_pixels_sha256')
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError('Image fingerprint required')
        if digest in seen:
            continue
        seen.add(digest)
        structured = observation.get('structured_observations')
        if not isinstance(structured, dict) or set(structured) != set(FIELDS):
            raise ValueError('Missing validated VLM structured observations')
        for field in FIELDS:
            finding = structured[field]
            if not isinstance(finding, dict) or finding.get('verified') is not False:
                raise ValueError('Expected unverified structured AI observation')
            value = finding.get('value')
            if value is not None:
                grouped[field].append({
                    'value': value, 'evidence': finding.get('visual_evidence'),
                    'uncertain': finding.get('uncertain'),
                    'source_image_sha256': digest,
                })
    hypotheses = {}
    for field in FIELDS:
        candidates = grouped[field]
        distinct = {str(item['value']) for item in candidates}
        hypotheses[field] = {
            'candidate_observations': candidates,
            'status': ('unknown' if not candidates else
                       'conflict' if len(distinct) > 1 else 'unverified_agreement'),
            'user_approval_required': True,
        }
    return {
        'schema': 'bimai360.vlm_multiview_consensus.v156',
        'project_id': project,
        'distinct_image_count': len(seen),
        'hypotheses': hypotheses,
        'geometry_verified': False,
        'ifc_export_ready': False,
    }
