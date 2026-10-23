"""Shared streaming verification of a completed LoRA checkpoint."""
import hashlib
import json
import re
from safetensors import SafetensorError, safe_open
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
        # A matching checksum proves file integrity, not that bytes encode a
        # usable LoRA. Read the safetensors index without allocating tensors.
        with safe_open(str(weights), framework='pt', device='cpu') as adapter:
            tensor_keys = list(adapter.keys())
            if not tensor_keys:
                return {'valid': False, 'reason': 'LoRA checkpoint has no tensors'}
            # Inspect headers only: no tensor payloads are loaded into memory.
            key_lookup = {name.lower(): name for name in tensor_keys}
            paired = 0
            seen_down = False
            for lower_name, actual_name in key_lookup.items():
                marker = next((
                    (down, up) for down, up in (
                        ('.lora_down.', '.lora_up.'),
                        ('.lora_a.', '.lora_b.'),
                    ) if down in lower_name
                ), None)
                if marker is None:
                    continue
                seen_down = True
                down, up = marker
                partner_lower = lower_name.replace(down, up, 1)
                partner_name = key_lookup.get(partner_lower)
                if partner_name is None:
                    return {'valid': False, 'reason': 'Unpaired LoRA down tensor'}
                shape_down = adapter.get_slice(actual_name).get_shape()
                shape_up = adapter.get_slice(partner_name).get_shape()
                if (
                    len(shape_down) != 2 or len(shape_up) != 2
                    or any(dim <= 0 for dim in (*shape_down, *shape_up))
                    or shape_down[0] != shape_up[1]
                ):
                    return {'valid': False, 'reason': 'Incompatible LoRA up/down tensor shapes'}
                paired += 1
            if not seen_down or not paired:
                return {'valid': False, 'reason': 'No matching LoRA up/down tensor pair'}
            # Reject orphaned up factors as well: a partially written adapter
            # can otherwise pass when at least one other pair is complete.
            for lower_name in key_lookup:
                for down, up in (
                    ('.lora_down.', '.lora_up.'),
                    ('.lora_a.', '.lora_b.'),
                ):
                    if up in lower_name:
                        counterpart = lower_name.replace(up, down, 1)
                        if counterpart not in key_lookup:
                            return {'valid': False, 'reason': 'Unpaired LoRA up tensor'}
                        break
        if isinstance(record.get('tensor_count'), int) and record['tensor_count'] != len(tensor_keys):
            return {'valid': False, 'reason': 'LoRA tensor count mismatch'}
        return {'valid': True, 'sha256': digest, 'bytes': expected_size,
                'tensor_count': len(tensor_keys)}
    except (OSError, ValueError, TypeError, ImportError, SafetensorError) as exc:
        return {'valid': False, 'reason': str(exc)[:160]}


def verified_adapters(root):
    root = Path(root)
    if not root.is_dir():
        return []
    return [item.name for item in sorted(root.iterdir())
            if item.is_dir() and validate_adapter(item)['valid']]
