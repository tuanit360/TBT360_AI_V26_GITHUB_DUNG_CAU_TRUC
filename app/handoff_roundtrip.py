"""Verify real exported BIM files, independently of in-memory export status."""
import hashlib
import json
from pathlib import Path
from app.bim_transaction import canonical_checksum
from app.schematic_delivery_audit import audit_schematic_building


def verify_exported_handoff(folder, expected_model):
    base = Path(folder)
    required = ('canonical_bim_handoff.json', 'schematic_walls.glb',
                'schematic_plan.dxf', 'plan.svg', 'front_elevation.svg',
                'schematic_wall_id_mapping.json')
    absent = [name for name in required if not (base / name).is_file()
              or (base / name).stat().st_size == 0]
    if absent:
        raise ValueError('Thiếu dữ liệu bàn giao: ' + ', '.join(absent))
    reopened = json.loads((base / required[0]).read_text(encoding='utf-8'))
    model_audit = audit_schematic_building(reopened)
    if canonical_checksum(reopened) != canonical_checksum(expected_model):
        raise ValueError('BIM JSON mở lại không khớp mô hình đã tạo')
    mapping = json.loads((base / 'schematic_wall_id_mapping.json').read_text(encoding='utf-8'))
    entities = reopened['entities']
    for key, category in (('canonical_wall_entity_ids', 'wall'),
                          ('canonical_slab_entity_ids', 'slab'),
                          ('canonical_roof_entity_ids', 'roof')):
        identifiers = sorted(e['id'] for e in entities if e['category'] == category)
        if sorted(mapping.get(key, [])) != identifiers:
            raise ValueError('Danh sách ID 3D không khớp BIM JSON: ' + category)
    data = (base / 'schematic_walls.glb').read_bytes()
    if data[:4] != b'glTF':
        raise ValueError('Tệp GLB không có cấu trúc nhị phân glTF')
    try:
        import trimesh
        scene = trimesh.load(str(base / 'schematic_walls.glb'), force='scene')
    except Exception as exc:
        raise ValueError('Không thể mở lại mô hình GLB') from exc
    if not scene.geometry or sum(len(g.faces) for g in scene.geometry.values()) == 0:
        raise ValueError('Mô hình GLB không có hình học tam giác')
    dxf = (base / 'schematic_plan.dxf').read_text(encoding='utf-8')
    if 'SECTION' not in dxf or 'ENTITIES' not in dxf or 'EOF' not in dxf:
        raise ValueError('Tệp DXF chưa có cấu trúc cơ bản hợp lệ')
    for name in ('plan.svg', 'front_elevation.svg'):
        from xml.etree import ElementTree
        root = ElementTree.parse(base / name).getroot()
        if not root.tag.endswith('svg'):
            raise ValueError('Không đọc được hình chiếu SVG')
    hashes = {
        name: hashlib.sha256((base / name).read_bytes()).hexdigest()
        for name in required
    }
    return {
        'trang_thai': 'ĐÃ MỞ LẠI CÁC TỆP BÀN GIAO',
        'ket_qua_hinh_hoc': model_audit,
        'so_mesh_glb': len(scene.geometry),
        'so_mat_tam_giac_glb': sum(len(g.faces) for g in scene.geometry.values()),
        'sha256_tung_tep': hashes,
        'xac_minh_ifc': False,
        'kiem_tra_thiet_ke_ky_thuat': False,
    }
