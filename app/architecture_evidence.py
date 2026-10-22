"""Strict evidence-gated VLM observations and user-approved BIM constraints.

The model's output is untrusted. Only a user-approved hypothesis with
explicit dimensions can be passed to schematic BIM synthesis.
"""
import json
import re

FIELDS = ('building_type', 'floor_count', 'roof_type', 'facade_system')
ALLOWED = set(FIELDS)


def parse_vlm_observations(raw_text):
    if not isinstance(raw_text, str) or len(raw_text) > 16000:
        raise ValueError('Invalid model output size')
    cleaned = raw_text.strip()
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^\x60{3}(?:json)?\s*|\s*\x60{3}$', '', cleaned, flags=re.I).strip()
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError('VLM must return a valid JSON object') from exc
    if not isinstance(data, dict) or set(data) != {'observations'}:
        raise ValueError('Unexpected VLM response schema')
    observations = data['observations']
    if not isinstance(observations, dict) or set(observations) != ALLOWED:
        raise ValueError('Architecture observation fields are incomplete')
    result = {}
    for field in FIELDS:
        item = observations[field]
        if not isinstance(item, dict) or set(item) != {'value', 'evidence', 'uncertain'}:
            raise ValueError('Observation must include value, evidence and uncertainty')
        value, evidence, uncertain = item['value'], item['evidence'], item['uncertain']
        if not isinstance(uncertain, bool):
            raise ValueError('Uncertainty must be boolean')
        if value is not None and (isinstance(value, bool) or
                (field == 'floor_count' and
                 (type(value) is not int or not 1 <= value <= 200)) or
                (field != 'floor_count' and
                 (not isinstance(value, str) or len(value) > 160))):
            raise ValueError('Invalid architecture value')
        if not isinstance(evidence, str) or len(evidence) > 300:
            raise ValueError('Invalid evidence')
        if value is not None and not evidence.strip():
            raise ValueError('Nonempty evidence required for any proposed value')
        result[field] = {'value': value, 'visual_evidence': evidence,
                         'uncertain': uncertain, 'verified': False}
    return result


def approve_schematic_from_vlm(observation, approved_constraints):
    """Explicit user approval required before a VLM proposal affects geometry."""
    from app.schematic_architecture import create_schematic
    if not isinstance(observation, dict) or not observation.get('model_inference_performed'):
        raise ValueError('Actual inference record required')
    if 'structured_observations' not in observation:
        raise ValueError('No structured observations')
    if not isinstance(approved_constraints, dict) or set(approved_constraints) != {
        'width_m', 'depth_m', 'floor_height_m', 'floor_count', 'user_approved'
    } or approved_constraints['user_approved'] is not True:
        raise ValueError('Explicit complete user design constraints required')
    floors = approved_constraints['floor_count']
    if type(floors) is not int:
        raise ValueError('Floor count must be a positive integer')
    model = create_schematic(observation['project_id'], approved_constraints['width_m'],
                             approved_constraints['depth_m'],
                             approved_constraints['floor_height_m'], floors)
    model['concept_source'] = {
        'observation_image_sha256': observation['image_pixels_sha256'],
        'model_inference_performed': True,
        'derived_dimensions_from_image': False,
        'dimensions_entered_and_approved_by_user': True,
        'architecture_observations_are_unverified': True,
    }
    return model
