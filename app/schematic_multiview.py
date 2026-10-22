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
    if len(model.get('levels', [])) != count or len(model.get('entities', [])) != count * 4:
        raise ValueError('Canonical shell entities/levels do not match parameters')
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
