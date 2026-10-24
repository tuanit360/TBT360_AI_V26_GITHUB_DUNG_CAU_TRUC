"""Volume contract between canonical BIM wall/slab/openings and exported GLB.

Compares actual reopened solids rather than relying only on file presence.
The conceptual roof is an open surface and is deliberately excluded.
"""
import math


def expected_solid_volume(model):
    entities = model['entities']
    walls = {e['id']: e for e in entities if e['category'] == 'wall'}
    volume = 0.0
    for wall in walls.values():
        g = wall['geometry']
        segment_length = math.dist(g['origin'], g['endpoint'])
        volume += segment_length * g['height'] * g['thickness']
    for slab in (e for e in entities if e['category'] == 'slab'):
        g = slab['geometry']
        volume += g['width'] * g['depth'] * g['thickness']
    for opening in (e for e in entities if e['category'] in ('door', 'window')):
        host = walls.get(opening.get('host_id'))
        if host is None:
            raise ValueError('Cửa không có tường chủ hợp lệ')
        geometry = opening['geometry']
        volume -= geometry['width_m'] * geometry['height_m'] * host['geometry']['thickness']
    if not math.isfinite(volume) or volume <= 0:
        raise ValueError('Thể tích dự kiến không hợp lệ')
    return volume


def validate_reopened_mesh_volume(scene, model, tolerance_m3=0.005):
    target = expected_solid_volume(model)
    nodes = list(scene.graph.nodes_geometry)
    if not nodes:
        raise ValueError('GLB không có cấu kiện hình học')
    actual = 0.0
    for node in nodes:
        transform, geometry_name = scene.graph.get(node)
        if node == 'ROOF_MAIN' or geometry_name == 'ROOF_MAIN':
            continue
        part = scene.geometry[geometry_name].copy()
        part.apply_transform(transform)
        actual += abs(part.volume)
    if abs(actual-target) > tolerance_m3:
        raise ValueError(
            'Thể tích GLB không khớp dữ liệu BIM: '
            f'{actual:.4f} m³ so với {target:.4f} m³')
    return {
        'the_tich_bim_du_kien_m3': round(target, 5),
        'the_tich_glb_mo_lai_m3': round(actual, 5),
        'sai_lech_m3': round(abs(actual-target), 6),
        'gioi_han_sai_so_m3': tolerance_m3,
        'mai_duoc_kiem_tra_the_tich': False,
        'ket_qua': 'ĐẠT ĐỐI CHIẾU THỂ TÍCH TƯỜNG / SÀN / LỖ MỞ',
    }
