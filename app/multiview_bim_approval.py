"""Evidence-gated transition from multiple VLM views to one BIM concept.

Contradictions must be reviewed explicitly, with user-entered dimensions.
This never upgrades AI hypotheses into verified survey measurements.
"""
import re
from app.architecture_evidence import approve_schematic_from_vlm

SHA = re.compile(r'^[0-9a-f]{64}$')


def approve_multiview_concept(observations, reconciliation, constraints, acknowledged_conflicts=False):
    if not isinstance(observations, list) or not observations:
        raise ValueError('Observation source records required')
    if not isinstance(reconciliation, dict) or reconciliation.get('schema') != 'bimai360.vlm_multiview_consensus.v156':
        raise ValueError('Valid reconciliation report required')
    from app.architecture_multiview import reconcile_architecture_observations
    expected = reconcile_architecture_observations(observations)
    if reconciliation != expected:
        raise ValueError('Reconciliation differs from source observations')
    if len(observations) > 12:
        raise ValueError('Maximum twelve images per batch')
    conflicts = sorted(
        key for key, record in expected['hypotheses'].items()
        if record['status'] == 'conflict'
    )
    if conflicts and acknowledged_conflicts is not True:
        raise ValueError('Resolve or explicitly acknowledge conflicting AI observations')
    floor_record = expected['hypotheses']['floor_count']
    if floor_record['status'] == 'unverified_agreement':
        proposed = floor_record['candidate_observations'][0]['value']
        if constraints.get('floor_count') != proposed and acknowledged_conflicts is not True:
            raise ValueError('Explicitly acknowledge floor count different from AI proposal')
    source = observations[0]
    model = approve_schematic_from_vlm(source, constraints)
    source_hashes = sorted({
        item['image_pixels_sha256'] for item in observations
    })
    if any(not SHA.fullmatch(digest) for digest in source_hashes):
        raise ValueError('Invalid image fingerprint')
    model['concept_source']['observation_image_sha256_list'] = source_hashes
    model['concept_source']['multiview_conflict_fields'] = conflicts
    model['concept_source']['conflicts_acknowledged_by_user'] = acknowledged_conflicts is True
    model['concept_source']['hypothesis_verification'] = 'not_verified'
    model['concept_source']['floor_count_source'] = 'explicit_user_approved_constraints'
    return model
