"""Canonical gable roof with physically distinct pitched surfaces.

Concept geometry comes from user-approved width/depth and pitch, not
reconstructed from an image. Ridge runs along Y at the building centre.
"""
from copy import deepcopy
import math
from app.bim_transaction import validate_document


def add_gable_roof(document, pitch_degrees=30, overhang_m=0.3):
    validate_document(document)
    if type(pitch_degrees) not in (float, int) or not 10 <= pitch_degrees <= 55:
        raise ValueError('Pitch must be 10–55 degrees')
    if type(overhang_m) not in (float, int) or not 0 <= overhang_m <= 1:
        raise ValueError('Overhang must be 0–1 metres')
    result = deepcopy(document)
    params = result.get('scheme_parameters')
    if not isinstance(params, dict):
        raise ValueError('User-dimensioned canonical shell required')
    if any(item['id'] == 'ROOF_MAIN' for item in result['entities']):
        raise ValueError('Roof already exists')
    width, depth = params['width_m'], params['depth_m']
    top = max(level['elevation'] for level in result['levels']) + params['floor_height_m']
    rise = (width / 2 + overhang_m) * math.tan(math.radians(pitch_degrees))
    result['entities'].append({
        'id': 'ROOF_MAIN', 'category': 'roof',
        'level_id': result['levels'][-1]['id'],
        'verification': 'concept',
        'geometry': {
            'roof_style': 'gable', 'pitch_degrees': float(pitch_degrees),
            'overhang_m': float(overhang_m), 'ridge_height_m': round(top + rise, 6),
            'eave_height_m': round(top, 6),
            'width_m': width, 'depth_m': depth,
        },
    })
    validate_document(result)
    return result


def gable_mesh(document):
    validate_document(document)
    roofs = [e for e in document['entities'] if e['id'] == 'ROOF_MAIN' and e['category'] == 'roof']
    if len(roofs) != 1:
        raise ValueError('Expected one canonical gable roof')
    g = roofs[0]['geometry']
    width, depth, overhang = g['width_m'], g['depth_m'], g['overhang_m']
    eave, ridge = g['eave_height_m'], g['ridge_height_m']
    y0, y1 = -overhang, depth + overhang
    x0, xc, x1 = -overhang, width/2, width + overhang
    vertices = [[x0,y0,eave],[xc,y0,ridge],[x1,y0,eave],
                [x0,y1,eave],[xc,y1,ridge],[x1,y1,eave]]
    faces = [[0,1,4],[0,4,3],[1,2,5],[1,5,4]]
    return {'entity_id': 'ROOF_MAIN', 'vertices_m': vertices,
            'triangles': faces, 'watertight': False,
            'geometry_source': 'explicit_user_dimensions'}
