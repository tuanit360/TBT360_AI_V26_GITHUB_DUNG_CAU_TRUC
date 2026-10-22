"""V79 local inference readiness and conservative CPU planning.

This module never downloads models or claims inference succeeded.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def inspect_local_assets(root, *, cuda_available=False):
    root = Path(root)
    folder = root / 'models' / 'sd15'
    index = folder / 'model_index.json'
    status = {
        'model_found': index.is_file(),
        'model_valid_index': False,
        'model_path': str(folder),
        'cuda_available': bool(cuda_available),
        'lora_verified_count': 0,
        'recommended_preset': 'Xem nhanh · ít VRAM',
        'recommended_steps': 15,
        'recommended_count': 1,
        'generation_verified': False,
        'issues': [],
    }
    if not index.is_file():
        status['issues'].append('Chưa thấy model SD1.5 cục bộ. Muốn chạy offline cần tải model riêng.')
    else:
        try:
            data = json.loads(index.read_text(encoding='utf-8'))
            if not isinstance(data, dict) or '_class_name' not in data:
                status['issues'].append('model_index.json không đúng cấu trúc Diffusers.')
            else:
                status['model_valid_index'] = True
        except (ValueError, OSError, UnicodeError):
            status['issues'].append('Không đọc được model_index.json.')
    if not cuda_available:
        status['issues'].append('CPU-only: sinh ảnh diffusion có thể rất chậm; nên tạo 1 phương án với 15 bước.')
    lora_dir = root / 'loras'
    if lora_dir.is_dir():
        import hashlib
        for item in lora_dir.iterdir():
            if not item.is_dir():
                continue
            meta = item / 'training_status.json'
            weights = item / 'pytorch_lora_weights.safetensors'
            if not (meta.is_file() and weights.is_file()):
                continue
            try:
                record = json.loads(meta.read_text(encoding='utf-8'))
                if record.get('status') != 'SUCCEEDED' or record.get('weights_bytes') != weights.stat().st_size:
                    continue
                if hashlib.sha256(weights.read_bytes()).hexdigest() == record.get('weights_sha256'):
                    status['lora_verified_count'] += 1
            except (OSError, ValueError, TypeError):
                continue
    if status['lora_verified_count'] == 0:
        status['issues'].append('Chưa có LoRA được xác minh SHA256; có thể dùng model nền.')
    return status
