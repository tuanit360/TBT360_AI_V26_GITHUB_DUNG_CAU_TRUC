"""Shared streaming verification of a completed LoRA checkpoint."""
import hashlib
import json
import re
from pathlib import Path


def validate_adapter(folder):
    folder = Path(folder)
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', folder.name):
        return {'valid': False, 'reason': 'Invalid adapter name'}
    weights = folder / 'pytorch_lora_weights.safetensors'
    status = folder / 'training_status.json'
    try:
        record = json.loads(status.read_text(encoding='utf-8'))
        if record.get('status') != 'SUCCEEDED':
            return {'valid': False, 'reason': 'Training did not succeed'}
        expected_size = record.get('weights_bytes')
        if not isinstance(expected_size, int) or expected_size <= 0:
            return {'valid': False, 'reason': 'Missing weight size'}
        if weights.stat().st_size != expected_size:
            return {'valid': False, 'reason': 'Weight size mismatch'}
        with weights.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != record.get('weights_sha256'):
            return {'valid': False, 'reason': 'SHA256 mismatch'}
        return {'valid': True, 'sha256': digest, 'bytes': expected_size}
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return {'valid': False, 'reason': str(exc)[:160]}


def verified_adapters(root):
    root = Path(root)
    if not root.is_dir():
        return []
    return [item.name for item in sorted(root.iterdir())
            if item.is_dir() and validate_adapter(item)['valid']]
