"""V162–V166: auditably map AI evidence to advisory design constraints.

AI-observed apparent floors and facade/roof descriptions never become
measured building geometry. Only approved metric constraints create BIM.
"""
from app.multiview_bim_approval import approve_multiview_concept


def create_reviewed_architecture_proposal(observations, constraints, acknowledge=False):
    from app.architecture_multiview import reconcile_architecture_observations
    review = reconcile_architecture_observations(observations)
    canonical = approve_multiview_concept(observations, review, constraints, acknowledge)
    advisory = {}
    for field, finding in review['hypotheses'].items():
        candidates = finding['candidate_observations']
        advisory[field] = {
            'status': finding['status'],
            'unverified_values': sorted({str(row['value']) for row in candidates}),
            'source_count': len(candidates),
            'use_for_geometry': False,
        }
    canonical['design_evidence_review'] = {
        'schema': 'bimai360.design_evidence_review.v166',
        'advisory_hypotheses': advisory,
        'geometry_dimensions_source': 'user_confirmed',
        'automatic_roof_or_facade_geometry': False,
        'engineering_verified': False,
    }
    return canonical, review


def verify_reviewed_proposal(canonical, observations, constraints, acknowledge=False):
    """Detect accidental geometry mutation or lost visual evidence after handoff."""
    from app.bim_transaction import canonical_checksum, validate_document
    validate_document(canonical)
    expected, review = create_reviewed_architecture_proposal(
        observations, constraints, acknowledge
    )
    if canonical_checksum(expected) != canonical_checksum(canonical):
        raise ValueError('BIM proposal differs from approved architecture evidence')
    return {'valid': True, 'checksum': canonical_checksum(canonical),
            'source_images': review['distinct_image_count'],
            'geometry_source': 'user_confirmed', 'ifc_export_ready': False}
