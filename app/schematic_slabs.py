"""Attach real conceptual slabs to the same canonical levels used by walls."""
from copy import deepcopy
from app.bim_transaction import validate_document


def add_schematic_slabs(document, slab_thickness=0.2):
    validate_document(document)
    if type(slab_thickness) not in (int, float) or not 0.1 <= slab_thickness <= 0.6:
        raise ValueError('Slab thickness outside schematic range')
    model = deepcopy(document)
    params = model.get('scheme_parameters')
    if not isinstance(params, dict):
        raise ValueError('Requires dimensioned schematic shell')
    w, d = params['width_m'], params['depth_m']
    existing = {e['id'] for e in model['entities']}
    for level in model['levels']:
        entity_id = 'SLAB_' + level['id']
        if entity_id in existing:
            raise ValueError('Slab already exists')
        model['entities'].append({
            'id': entity_id, 'category': 'slab', 'level_id': level['id'],
            'verification': 'concept', 'geometry': {
                'origin': [0, 0, level['elevation']], 'width': w,
                'depth': d, 'thickness': float(slab_thickness),
            },
        })
    validate_document(model)
    return model


def slab_mesh_data(model):
    validate_document(model)
    geometry = []
    for entity in model['entities']:
        if entity['category'] != 'slab':
            continue
        g = entity['geometry']
        x, y, z = g['origin']
        w, d, t = g['width'], g['depth'], g['thickness']
        if not all(type(v) in (float, int) and 0 < v < 1000
                   for v in (w, d, t)):
            raise ValueError('Invalid slab dimensions')
        geometry.append((entity['id'], [x, y, z-t], [x+w, y+d, z]))
    return geometry
