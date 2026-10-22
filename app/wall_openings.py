"""Rectangular wall cut-outs using non-overlapping solid strips.

Parametric 3D construction stays attached to the canonical wall's ID.
There is no fake transparent decal posing as a wall opening.
"""
import math
from copy import deepcopy
from app.bim_transaction import validate_document


def add_wall_opening(document, wall_id, opening_id, offset_m, sill_m, width_m, height_m):
    validate_document(document)
    model = deepcopy(document)
    walls = [e for e in model['entities'] if e['id'] == wall_id and e['category'] == 'wall']
    if len(walls) != 1 or any(e['id'] == opening_id for e in model['entities']):
        raise ValueError('Invalid wall host or duplicate opening ID')
    wall = walls[0]
    g = wall['geometry']
    length = math.dist(g['origin'][:2], g['endpoint'][:2])
    values = (offset_m, sill_m, width_m, height_m)
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
        raise ValueError('Opening dimensions must be finite')
    if (offset_m < 0.1 or sill_m < 0 or width_m < 0.6 or height_m < 0.6
            or offset_m + width_m > length - 0.1
            or sill_m + height_m > g['height'] - 0.1):
        raise ValueError('Opening exceeds wall boundaries')
    for entity in model['entities']:
        if entity.get('category') != 'opening' or entity.get('host_id') != wall_id:
            continue
        other = entity['geometry']
        if (offset_m < other['offset_m'] + other['width_m'] and
                other['offset_m'] < offset_m + width_m and
                sill_m < other['sill_m'] + other['height_m'] and
                other['sill_m'] < sill_m + height_m):
            raise ValueError('Opening overlaps an existing opening')
    model['entities'].append({
        'id': opening_id, 'category': 'opening', 'level_id': wall['level_id'],
        'host_id': wall_id, 'verification': 'concept',
        'geometry': {'offset_m': float(offset_m), 'sill_m': float(sill_m),
                     'width_m': float(width_m), 'height_m': float(height_m)},
    })
    validate_document(model)
    return model


def wall_solid_parts(document, wall_id):
    validate_document(document)
    wall = next((e for e in document['entities'] if e['id'] == wall_id and e['category'] == 'wall'), None)
    if wall is None:
        raise ValueError('Missing canonical wall')
    g = wall['geometry']
    length = math.dist(g['origin'][:2], g['endpoint'][:2])
    openings = [e['geometry'] for e in document['entities']
                if e['category'] == 'opening' and e.get('host_id') == wall_id]
    boundaries = sorted({0.0, length} |
                        {v for o in openings for v in (o['offset_m'], o['offset_m']+o['width_m'])})
    solids = []
    for left, right in zip(boundaries, boundaries[1:]):
        if right-left < 1e-8:
            continue
        intervals = [(0.0, g['height'])]
        for item in openings:
            if item['offset_m'] < right-1e-8 and item['offset_m']+item['width_m'] > left+1e-8:
                bottom, top = item['sill_m'], item['sill_m']+item['height_m']
                intervals = [(a, b) for low, high in intervals
                             for a, b in ((low, min(high, bottom)), (max(low, top), high))
                             if b-a > 1e-8]
        for low, high in intervals:
            solids.append((left, right, low, high))
    return solids
