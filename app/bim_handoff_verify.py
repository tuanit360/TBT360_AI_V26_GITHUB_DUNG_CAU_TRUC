"""V94 contract verification for saved BIM handoff without side effects."""
import hashlib
import json
from pathlib import Path
from app.canonical_bim_contract import build_handoff, SCHEMA


def verify_saved_handoff(file_path):
    path = Path(file_path)
    try:
        source = path.read_bytes()
        data = json.loads(source)
        if data.get('schema') != SCHEMA:
            raise ValueError('Sai schema BIM handoff')
        regenerated = build_handoff(
            data['project_id'], units=data['units'],
            level_ids=data.get('levels'), elements=data.get('entities'),
        )
        if (data.get('ifc_export_ready') is not False or
                data.get('bim_2d_projection_source') != 'canonical_entities_only' or
                data.get('bim_3d_projection_source') != 'canonical_entities_only'):
            raise ValueError('File tự nhận capability chưa được kiểm chứng')
        if regenerated['entities'] != data.get('entities'):
            raise ValueError('Sai khác dữ liệu canonical')
        return {'valid': True, 'sha256': hashlib.sha256(source).hexdigest(),
                'entities': len(regenerated['entities']), 'levels': len(regenerated['levels']),
                'ifc_export_ready': False}
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        return {'valid': False, 'reason': str(exc)[:250]}
