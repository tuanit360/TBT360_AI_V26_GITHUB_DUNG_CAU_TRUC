"""Project-axis elevations and section from the canonical schematic shell.

These views are drawn from user-entered dimensions and level elevations,
not inferred from photos, and remain concept-only.
"""
from app.schematic_architecture import create_schematic


def schematic_multiview(model):
    parameters = model.get('scheme_parameters')
    if not isinstance(parameters, dict):
        raise ValueError('Missing schematic parameters')
    w = float(parameters['width_m'])
    d = float(parameters['depth_m'])
    height = float(parameters['floor_height_m'])
    count = int(parameters['floor_count'])
    from app.schematic_architecture import create_schematic
    from app.bim_transaction import validate_document
    validate_document(model)
    expected = create_schematic(model['project_id'], w, d, height, count)
    actual_walls = {
        entity['id']: entity
        for entity in model['entities'] if entity['category'] == 'wall'
    }
    expected_walls = {
        entity['id']: entity
        for entity in expected['entities']
    }
    if len(model.get('levels', [])) != count or set(actual_walls) != set(expected_walls):
        raise ValueError('Số tầng hoặc tường vỏ không khớp thông số')
    for actual_level, expected_level in zip(model['levels'], expected['levels']):
        if (actual_level['id'] != expected_level['id']
                or abs(actual_level['elevation'] - expected_level['elevation']) > 1e-5):
            raise ValueError('Cao độ tầng không khớp thông số')
    for identity, canonical in expected_walls.items():
        actual = actual_walls[identity]
        if (actual['level_id'] != canonical['level_id']
                or actual['geometry'] != canonical['geometry']):
            raise ValueError('Hình học tường vỏ không khớp thông số')
    # Slabs, roof, doors and windows may legitimately share this canonical
    # model and do not invalidate the projection.
    scale = 20
    def view(horizontal):
        width = round(horizontal * scale + 40)
        tall = round(height * count * scale + 40)
        body = [f'<rect x="20" y="20" width="{horizontal*scale}" height="{height*count*scale}" fill="none" stroke="black" stroke-width="2"/>']
        body += [f'<line x1="20" y1="{20+i*height*scale}" x2="{20+horizontal*scale}" y2="{20+i*height*scale}" stroke="black"/>'
                 for i in range(1, count)]
        return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {tall}">' + ''.join(body) + '</svg>'
    return {
        'front_elevation.svg': view(w),
        'rear_elevation.svg': view(w),
        'left_elevation.svg': view(d),
        'right_elevation.svg': view(d),
        'longitudinal_section.svg': view(d),
        'cross_section.svg': view(w),
        'view_meta': {'source': 'same_canonical_schematic_parameters',
                      'verified_bim_geometry': False,
                      'views_are_concept_diagrams': True,
                      'rooms_stairs_mep_not_modeled': True},
    }
