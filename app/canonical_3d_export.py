"""Export a genuine 3D GLB mesh from user-approved canonical wall geometry.

This is metric schematic wall massing, not photo-reconstructed BIM. Every
mesh part is derived from the wall baselines and retains its canonical ID.
"""
import math
from app.bim_transaction import validate_document


def canonical_wall_mesh(model):
    validate_document(model)
    vertices, faces, ids = [], [], []
    for entity in model['entities']:
        if entity.get('category') != 'wall':
            continue
        geom = entity.get('geometry', {})
        origin, endpoint = geom.get('origin'), geom.get('endpoint')
        if not isinstance(origin, list) or not isinstance(endpoint, list) or len(origin) != 3 or len(endpoint) != 3:
            raise ValueError('Wall requires 3D start and end')
        if any(type(x) not in (float, int) or not math.isfinite(x) for x in origin + endpoint):
            raise ValueError('Wall coordinates must be finite')
        thick, height = geom.get('thickness'), geom.get('height')
        if type(thick) not in (float, int) or type(height) not in (float, int) or not (0.05 <= thick <= 2 and 2 <= height <= 20):
            raise ValueError('Invalid wall dimensions')
        dx, dy = endpoint[0] - origin[0], endpoint[1] - origin[1]
        length = math.hypot(dx, dy)
        if length < 0.01 or abs(endpoint[2] - origin[2]) > 1e-6:
            raise ValueError('Degenerate or sloped wall')
        nx, ny = -dy / length * thick / 2, dx / length * thick / 2
        corners = [(origin[0]+nx, origin[1]+ny),
                   (origin[0]-nx, origin[1]-ny),
                   (endpoint[0]-nx, endpoint[1]-ny),
                   (endpoint[0]+nx, endpoint[1]+ny)]
        base = len(vertices)
        z = origin[2]
        vertices.extend([[x, y, z + dz] for dz in (0, height) for x, y in corners])
        tris = [(0,2,1),(0,3,2),(4,5,6),(4,6,7),
                (0,1,5),(0,5,4),(1,2,6),(1,6,5),
                (2,3,7),(2,7,6),(3,0,4),(3,4,7)]
        faces.extend([[base + v for v in tri] for tri in tris])
        ids.append(entity['id'])
    if not ids:
        raise ValueError('No walls to export')
    return {'vertices_m': vertices, 'triangles': faces, 'wall_entity_ids': ids,
            'geometry_source': 'explicit_user_dimensions', 'verified': False}


def export_wall_glb(model, filename):
    """Real GLB geometry using optional trimesh, without fake placeholder content."""
    try:
        import numpy as np
        import trimesh
    except ImportError as exc:
        raise RuntimeError('GLB export requires trimesh and numpy') from exc
    mesh = canonical_wall_mesh(model)
    geometry = trimesh.Trimesh(vertices=np.asarray(mesh['vertices_m'], dtype=float),
                               faces=np.asarray(mesh['triangles'], dtype=int),
                               process=False)
    scene = trimesh.Scene(geometry)
    scene.metadata['source'] = 'BIMAI360 concept geometry; not photo-inferred IFC'
    scene.export(file_obj=str(filename), file_type='glb')
    return mesh
