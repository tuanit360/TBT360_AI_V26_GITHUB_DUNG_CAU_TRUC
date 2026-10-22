"""Deterministic zoning sketch from explicitly entered rectangle dimensions.

This is a conceptual 2-room suggestion, not a learned floor plan or verified
architecture. Entities and SVG come from identical canonical room geometry.
"""
from app.schematic_architecture import create_schematic


def add_two_zone_sketch(project_id, width, depth, floor_height=3.2):
    model = create_schematic(project_id, width, depth, floor_height, 1)
    width, depth = float(width), float(depth)
    partition_x = round(width * 0.55, 4)
    spaces = [
        ('ROOM_A', 'Flexible zone A', [0, 0, partition_x, depth]),
        ('ROOM_B', 'Flexible zone B', [partition_x, 0, width, depth]),
    ]
    for identity, label, bounds in spaces:
        model['entities'].append({
            'id': identity, 'level_id': 'L01', 'category': 'space',
            'verification': 'concept',
            'name': label,
            'geometry': {'bounds_xy': bounds, 'floor_z': 0.0, 'height': floor_height},
        })
    model['entities'].append({
        'id': 'PARTITION_01', 'level_id': 'L01', 'category': 'wall',
        'verification': 'concept',
        'geometry': {'origin': [partition_x, 0, 0],
                     'endpoint': [partition_x, depth, 0],
                     'height': floor_height, 'thickness': 0.15},
    })
    model['zoning'] = {'method': 'explicit_size_simple_55_45_split',
                       'not_image_inferred': True, 'room_adjacency': [['ROOM_A', 'ROOM_B']],
                       'door_positions_defined': False, 'code_compliance_verified': False}
    return model


def zoning_svg(model):
    params = model['scheme_parameters']
    width, depth = params['width_m'], params['depth_m']
    spaces = [entity for entity in model['entities'] if entity['category'] == 'space']
    if len(spaces) != 2:
        raise ValueError('Expected two conceptual zones')
    scale = 20
    shapes = []
    for entity in spaces:
        x0, y0, x1, y1 = entity['geometry']['bounds_xy']
        shapes.append(
            f'<rect x="{20+x0*scale}" y="{20+y0*scale}" '
            f'width="{(x1-x0)*scale}" height="{(y1-y0)*scale}" '
            'fill="none" stroke="black" stroke-width="2"/>')
    w, h = 40+width*scale, 40+depth*scale
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">'
            + ''.join(shapes) + '</svg>')
