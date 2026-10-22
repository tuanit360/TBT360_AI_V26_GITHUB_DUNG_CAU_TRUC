"""Validate conceptual zone geometry against the single canonical BIM model."""
import math
from app.bim_transaction import validate_document


def validate_zoning(model, tolerance=1e-6):
    validate_document(model)
    params = model.get('scheme_parameters', {})
    zoning = model.get('zoning', {})
    if zoning.get('method') != 'explicit_size_simple_55_45_split':
        raise ValueError('Unsupported zoning method')
    width = float(params['width_m'])
    depth = float(params['depth_m'])
    if not all(math.isfinite(x) and x > 0 for x in (width, depth)):
        raise ValueError('Invalid floorplate')
    spaces = [e for e in model['entities'] if e['category'] == 'space']
    partitions = [e for e in model['entities'] if e['id'] == 'PARTITION_01']
    if len(spaces) != 2 or len(partitions) != 1:
        raise ValueError('Expected two spaces and one shared partition')
    spaces = sorted(spaces, key=lambda item: item['geometry']['bounds_xy'][0])
    first, second = [e['geometry']['bounds_xy'] for e in spaces]
    for bounds in (first, second):
        if len(bounds) != 4 or any(
            type(value) not in (int, float) or not math.isfinite(value)
            for value in bounds
        ):
            raise ValueError('Invalid space bounds')
    if any(abs(a - b) > tolerance for a, b in (
        (first[0], 0), (first[1], 0), (first[3], depth),
        (second[1], 0), (second[2], width), (second[3], depth),
        (first[2], second[0]),
    )):
        raise ValueError('Spaces overlap or do not cover floorplate')
    partition = partitions[0]['geometry']
    expected = first[2]
    if any(abs(a - b) > tolerance for a, b in (
        (partition['origin'][0], expected),
        (partition['endpoint'][0], expected),
        (partition['origin'][1], 0),
        (partition['endpoint'][1], depth),
    )):
        raise ValueError('Partition does not match room boundary')
    area = width * depth
    return {
        'valid': True, 'project_id': model['project_id'], 'area_m2': round(area, 4),
        'zone_areas_m2': [round((first[2]-first[0])*depth, 4),
                          round((second[2]-second[0])*depth, 4)],
        'shared_partition_x_m': expected,
        'verified': 'geometric_consistency_only',
        'technical_compliance_verified': False,
        'ifc_export_ready': False,
    }
