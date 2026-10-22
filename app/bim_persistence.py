"""V107–V111 transactional canonical BIM persistence with integrity checks.

JSON is written to a temporary file then replaced atomically. The loaded
document must still satisfy the same 2D/3D canonical contract.
"""
import hashlib
import json
import os
import tempfile
from pathlib import Path

from app.bim_transaction import validate_document, canonical_checksum


def save_project(document, destination):
    validated = validate_document(document)
    target = Path(destination)
    if target.suffix.lower() != '.json':
        raise ValueError('BIM project must be a JSON file')
    target.parent.mkdir(parents=True, exist_ok=True)
    canonical = json.dumps(validated, ensure_ascii=False, sort_keys=True,
                           separators=(',', ':'), allow_nan=False).encode('utf-8')
    digest = hashlib.sha256(canonical).hexdigest()
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.bimai360_',
                                         suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(canonical)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        temporary = None
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    return {'path': str(target), 'sha256': digest,
            'entity_count': len(validated['entities']), 'level_count': len(validated['levels'])}


def open_project(filename, expected_sha256=None, max_bytes=32 * 1024 * 1024):
    file_path = Path(filename)
    if file_path.stat().st_size > max_bytes:
        raise ValueError('BIM project exceeds safe import limit')
    content = file_path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError('BIM project checksum mismatch')
    document = json.loads(content)
    canonical = validate_document(document)
    if canonical_checksum(canonical) != digest:
        raise ValueError('Canonical model differs from stored model')
    return canonical
