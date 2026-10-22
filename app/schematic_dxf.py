"""DXF R2010-style ASCII 2D schematic export from user-entered canonical shell.

Geometry uses real drawing units (meters), not SVG screen pixels. No IFC,
rooms, doors, MEP or photo-inferred geometry is invented.
"""
from app.bim_transaction import validate_document


def _number(value):
    return format(float(value), '.8g')


def _line(layer, start, end):
    data = ['0','LINE','8',layer,'10',_number(start[0]),'20',_number(start[1]),
            '30','0','11',_number(end[0]),'21',_number(end[1]),'31','0']
    return '\n'.join(data) + '\n'


def export_plan_dxf(document):
    validate_document(document)
    parameters = document.get('scheme_parameters')
    if not isinstance(parameters, dict):
        raise ValueError('Cần mô hình vỏ công trình có kích thước xác định')
    level_ids = {level['id'] for level in document['levels']}
    lines = []
    for entity in document['entities']:
        if entity.get('category') != 'wall':
            continue
        geometry = entity.get('geometry', {})
        origin = geometry.get('origin')
        endpoint = geometry.get('endpoint')
        if (not isinstance(origin, list) or not isinstance(endpoint, list)
                or len(origin) != 3 or len(endpoint) != 3):
            raise ValueError('Tường thiếu đường cơ sở có hai điểm')
        if entity['level_id'] not in level_ids:
            raise ValueError('Tường thuộc tầng không tồn tại')
        lines.append(_line('WALL_' + entity['level_id'], origin, endpoint))
    if not lines:
        raise ValueError('Không có tường xuất bản vẽ')
    header = ('0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1024\n'
              '9\n$INSUNITS\n70\n6\n0\nENDSEC\n'
              '0\nSECTION\n2\nENTITIES\n')
    return header + ''.join(lines) + '0\nENDSEC\n0\nEOF\n'
