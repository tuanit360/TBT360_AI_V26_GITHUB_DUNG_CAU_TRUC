"""Independent post-export QA for conceptual BIM handoff geometry.

Checks intended parametric shell against canonical elements, including the
slabs/roof and openings that used to bypass the initial shell validator.
"""
import math
from app.bim_transaction import validate_document, canonical_checksum


def audit_schematic_building(model):
    validate_document(model)
    p = model.get('scheme_parameters')
    if not isinstance(p, dict):
        raise ValueError('Thiếu kích thước thiết kế đã nhập')
    width, depth, height, count = (p.get('width_m'), p.get('depth_m'),
                                   p.get('floor_height_m'), p.get('floor_count'))
    if any(type(x) not in (int, float) or not math.isfinite(x)
           for x in (width, depth, height)) or type(count) is not int:
        raise ValueError('Tham số công trình không hợp lệ')
    if len(model['levels']) != count:
        raise ValueError('Số tầng không khớp mô hình')
    ids = {e['id'] for e in model['entities']}
    walls, slabs, roof, openings = [], [], [], []
    for level_index, level in enumerate(model['levels']):
        if abs(level['elevation'] - level_index * height) > 1e-5:
            raise ValueError('Cao độ tầng không khớp kích thước')
        level_walls = [e for e in model['entities']
                       if e['category'] == 'wall' and e['level_id'] == level['id']]
        expected_edges = [
            ([0, 0], [width, 0]), ([width, 0], [width, depth]),
            ([width, depth], [0, depth]), ([0, depth], [0, 0])]
        if len(level_walls) != 4:
            raise ValueError('Mỗi tầng phải có bốn tường vỏ')
        for entity, (start, end) in zip(sorted(level_walls, key=lambda e:e['id']), expected_edges):
            g = entity['geometry']
            if (any(abs(g['origin'][j] - start[j]) > 1e-5 or
                    abs(g['endpoint'][j] - end[j]) > 1e-5 for j in range(2))
                    or abs(g['height'] - height) > 1e-5):
                raise ValueError('Hình học tường không khớp kích thước đã nhập')
        walls.extend(level_walls)
        level_slabs = [e for e in model['entities']
                       if e['category'] == 'slab' and e['level_id'] == level['id']]
        if len(level_slabs) != 1:
            raise ValueError('Thiếu sàn hoặc trùng sàn theo tầng')
        g = level_slabs[0]['geometry']
        if abs(g['width']-width)>1e-5 or abs(g['depth']-depth)>1e-5:
            raise ValueError('Kích thước sàn không khớp')
        slabs.extend(level_slabs)
    roof = [e for e in model['entities'] if e['category'] == 'roof']
    if len(roof) != 1:
        raise ValueError('Mô hình phải có đúng một mái concept')
    for e in model['entities']:
        if e['category'] in ('door', 'window'):
            if e.get('host_id') not in ids:
                raise ValueError('Lỗ mở không có tường chủ hợp lệ')
            openings.append(e)
    return {
        'ket_qua': 'ĐẠT KIỂM TRA HÌNH HỌC CONCEPT',
        'so_tang': count, 'so_tuong': len(walls), 'so_san': len(slabs),
        'so_mai': len(roof), 'so_cua_va_cua_so': len(openings),
        'dien_tich_san_m2': round(width*depth*count, 4),
        'ma_kiem_tra_sha256': canonical_checksum(model),
        'da_kiem_tra_thiet_ke_ky_thuat': False,
        'da_kiem_tra_ifc': False,
    }
