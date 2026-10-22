"""Schematic architecture from explicit user constraints, NOT from photograph inference.

A rectangular single-level proposal is an editable conceptual starting point.
One canonical wall set is used to derive the plan and front elevation SVGs.
"""
from app.canonical_bim_contract import build_handoff


def create_schematic(project_id, width_m, depth_m, height_m, floors=1):
    width, depth, height, count = float(width_m), float(depth_m), float(height_m), int(floors)
    if not (4 <= width <= 80 and 4 <= depth <= 80 and 2.4 <= height <= 6 and 1 <= count <= 20):
        raise ValueError('Giới hạn: rộng/sâu 4–80m, tầng 2.4–6m, số tầng 1–20')
    levels = [{'id': f'L{i + 1:02d}', 'elevation': round(i * height, 4)} for i in range(count)]
    walls = []
    edges = [(0, 0, width, 0), (width, 0, width, depth),
             (width, depth, 0, depth), (0, depth, 0, 0)]
    for index, level in enumerate(levels):
        for side, (x0, y0, x1, y1) in enumerate(edges, 1):
            walls.append({
                'id': f'W{index + 1:02d}_{side:02d}',
                'category': 'wall', 'level_id': level['id'],
                'verification': 'concept',
                'geometry': {
                    'origin': [x0, y0, level['elevation']],
                    'endpoint': [x1, y1, level['elevation']],
                    'height': height,
                    'thickness': 0.2,
                },
            })
    model = build_handoff(project_id, units='m', level_ids=levels, elements=walls)
    model['scheme_parameters'] = {
        'width_m': width, 'depth_m': depth, 'floor_height_m': height,
        'floor_count': count, 'source': 'explicit_user_constraints',
        'layout': 'empty_rectangular_shell_without_rooms',
    }
    return model


def render_views(model):
    params = model['scheme_parameters']
    w, d, h, floors = (params['width_m'], params['depth_m'],
                        params['floor_height_m'], params['floor_count'])
    def svg(lines, width, height):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
                + ''.join(lines) + '</svg>')
    scale = 20
    plan_w, plan_h = round(w * scale + 40), round(d * scale + 40)
    plan = svg([f'<rect x="20" y="20" width="{w * scale}" height="{d * scale}" '
                'fill="none" stroke="black" stroke-width="3"/>'], plan_w, plan_h)
    elev_w, elev_h = round(w * scale + 40), round(h * floors * scale + 40)
    elevation = svg([f'<rect x="20" y="20" width="{w * scale}" height="{h * floors * scale}" '
                     'fill="none" stroke="black" stroke-width="3"/>'] +
                    [f'<line x1="20" y1="{20 + i * h * scale}" x2="{20 + w * scale}" '
                     f'y2="{20 + i * h * scale}" stroke="black"/>'
                     for i in range(1, floors)], elev_w, elev_h)
    return {'plan.svg': plan, 'front_elevation.svg': elevation}
