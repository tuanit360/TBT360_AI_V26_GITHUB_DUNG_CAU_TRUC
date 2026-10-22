"""Conservative BIM handoff contract shared by architecture references.

Concept imagery never becomes a dimensioned BIM element automatically.
All prospective elements carry stable IDs and confidence/verification status.
"""
import json
import re
import math
from pathlib import Path

SCHEMA = 'tbt360.canonical_bim_handoff.v1'
CATEGORIES = {'wall', 'door', 'window', 'slab', 'roof', 'column', 'beam', 'stair', 'space'}
DIRECTIONS = {'concept', 'geometry_validated', 'engineering_verified'}


def build_handoff(project_id, *, units='m', level_ids=None, elements=None):
    if not isinstance(project_id, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{2,64}', project_id):
        raise ValueError('Mã công trình không hợp lệ')
    if units not in ('m', 'mm'):
        raise ValueError('Đơn vị phải m hoặc mm')
    levels = level_ids if level_ids is not None else []
    if not isinstance(levels, list) or any(
        not isinstance(item, dict) or
        not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', str(item.get('id', ''))) or
        (type(item.get('elevation')) not in (int, float) or not math.isfinite(item['elevation']))
        for item in levels
    ):
        raise ValueError('Danh sách tầng phải có ID và cao độ số')
    level_keys = [item['id'] for item in levels]
    if len(level_keys) != len(set(level_keys)):
        raise ValueError('ID tầng trùng')
    entities = elements if elements is not None else []
    if not isinstance(entities, list):
        raise ValueError('Danh sách cấu kiện không hợp lệ')
    seen = set()
    safe_entities = []
    for entity in entities:
        if not isinstance(entity, dict):
            raise ValueError('Cấu kiện không hợp lệ')
        identity = entity.get('id')
        if not isinstance(identity, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', identity):
            raise ValueError('UnifiedEntityId không hợp lệ')
        if identity in seen:
            raise ValueError('UnifiedEntityId trùng lặp')
        if entity.get('category') not in CATEGORIES:
            raise ValueError('Loại cấu kiện chưa hỗ trợ')
        if entity.get('level_id') not in level_keys:
            raise ValueError('Cấu kiện thiếu level hợp lệ')
        if entity.get('verification', 'concept') not in DIRECTIONS:
            raise ValueError('Trạng thái xác minh không hợp lệ')
        # Do not trust externally supplied engineering verification or unknown
        # semantic relationships without validating their basic shape.
        geometry = entity.get('geometry')
        if geometry is not None:
            if not isinstance(geometry, dict):
                raise ValueError('Geometry phải là object')
            coords = geometry.get('origin')
            if coords is not None and (
                not isinstance(coords, list) or len(coords) != 3 or
                any(type(number) not in (int, float) or not math.isfinite(number) for number in coords)
            ):
                raise ValueError('Tọa độ cấu kiện cần ba số hữu hạn')
        if entity.get('verification', 'concept') != 'concept' and geometry is None:
            raise ValueError('Không thể xác minh geometry nếu chưa có hình học')
        host = entity.get('host_id')
        if host is not None and (not isinstance(host, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', host)):
            raise ValueError('Host ID không hợp lệ')
        seen.add(identity)
        safe_entities.append(dict(entity))
    for entity in safe_entities:
        if entity.get('host_id') is not None:
            if entity['host_id'] == entity['id'] or entity['host_id'] not in seen:
                raise ValueError('Host tham chiếu chính nó hoặc cấu kiện không tồn tại')
    hosts = {entity['id']: entity.get('host_id') for entity in safe_entities}
    for entity_id in hosts:
        chain = set()
        current = entity_id
        while current is not None:
            if current in chain:
                raise ValueError('Phát hiện chu kỳ host relationships')
            chain.add(current)
            current = hosts.get(current)
    return {
        'schema': SCHEMA, 'project_id': project_id, 'units': units,
        'coordinate_system': 'local_project_unverified',
        'levels': levels, 'entities': safe_entities,
        'bim_2d_projection_source': 'canonical_entities_only',
        'bim_3d_projection_source': 'canonical_entities_only',
        'ifc_export_ready': False,
        'requires_geometry_review': True,
        'note': 'Concept entity hints are not verified 3D geometry or IFC.',
    }


def save_handoff(folder, handoff):
    if handoff.get('schema') != SCHEMA:
        raise ValueError('Unexpected handoff schema')
    output = Path(folder)
    output.mkdir(parents=True, exist_ok=True)
    path = output / 'canonical_bim_handoff.json'
    path.write_text(json.dumps(handoff, ensure_ascii=False, indent=2), encoding='utf-8')
    return path
