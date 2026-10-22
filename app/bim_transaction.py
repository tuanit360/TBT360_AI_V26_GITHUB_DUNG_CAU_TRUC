"""Validate canonical BIM handoffs and produce stable audit fingerprints.

No geometry is synthesized or upgraded from concept to verified BIM.
"""
from __future__ import annotations
import hashlib
import json
import math
from copy import deepcopy

from app.canonical_bim_contract import build_handoff


def canonical_checksum(document):
    normalized = json.dumps(
        document, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False,
    ).encode('utf-8')
    return hashlib.sha256(normalized).hexdigest()


def validate_document(document):
    if not isinstance(document, dict):
        raise ValueError('BIM document must be an object')
    rebuilt = build_handoff(
        document.get('project_id'),
        units=document.get('units'),
        level_ids=document.get('levels'),
        elements=document.get('entities'),
    )
    if document.get('schema') != rebuilt['schema']:
        raise ValueError('Unsupported BIM schema')
    if document.get('ifc_export_ready') is not False:
        raise ValueError('IFC capability must not be asserted for conceptual geometry')
    for field in ('coordinate_system', 'bim_2d_projection_source',
                  'bim_3d_projection_source'):
        if document.get(field) != rebuilt[field]:
            raise ValueError(f'Unexpected {field}')
    if document.get('requires_geometry_review') is not True:
        raise ValueError('Geometry review state must be preserved')
    return rebuilt


def apply_entity_update(document, entity_id, changes):
    """Immutable, all-or-nothing update; no silent edits to unrelated entities."""
    validate_document(document)
    if not isinstance(changes, dict) or not changes:
        raise ValueError('Changes must be a nonempty object')
    allowed = {'level_id', 'category', 'host_id', 'geometry', 'verification'}
    if not set(changes).issubset(allowed):
        raise ValueError('Unsupported or immutable entity property')
    updated = deepcopy(document)
    matches = [entity for entity in updated['entities'] if entity['id'] == entity_id]
    if len(matches) != 1:
        raise ValueError('Missing or duplicate UnifiedEntityId')
    matches[0].update(changes)
    validate_document(updated)
    return updated, {
        'operation': 'entity_update',
        'entity_id': entity_id,
        'before_sha256': canonical_checksum(document),
        'after_sha256': canonical_checksum(updated),
        'changed_paths': sorted(changes),
    }
