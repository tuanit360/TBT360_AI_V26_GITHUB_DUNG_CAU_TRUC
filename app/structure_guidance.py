"""V84 deterministic architectural structure-control preview.

Canny-like Sobel edge reference and side-by-side image comparison. These
are useful conditioning inputs; not proof a ControlNet has been run.
"""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageOps, ImageFilter


def structure_reference(image, threshold=80):
    if not isinstance(image, Image.Image):
        raise ValueError('Chọn ảnh kiến trúc trước')
    threshold = int(threshold)
    if not 1 <= threshold <= 254:
        raise ValueError('Ngưỡng cạnh phải từ 1 tới 254')
    source = ImageOps.exif_transpose(image).convert('RGB')
    if min(source.size) < 128:
        raise ValueError('Ảnh quá nhỏ để trích biên')
    # Suppress fine texture/shingle/tree grain while retaining principal edges.
    gray = source.convert('L').filter(ImageFilter.GaussianBlur(radius=1.4))
    edges = gray.filter(ImageFilter.FIND_EDGES)
    edges = edges.point(lambda value: 255 if value >= threshold else 0)
    edges = edges.filter(ImageFilter.MedianFilter(size=3))
    return edges.convert('RGB')


def export_structure_package(image, target, threshold=80, seed=42):
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    original = ImageOps.exif_transpose(image).convert('RGB')
    control = structure_reference(original, threshold)
    original.save(target / 'reference.png')
    control.save(target / 'edge_control.png')
    manifest = {
        'schema': 'tbt360.structure_reference.v84',
        'type': 'edge_preview_only_not_controlnet_inference',
        'threshold': int(threshold),
        'seed': int(seed),
        'image_size_px': list(original.size),
        'source_sha256': hashlib.sha256((target / 'reference.png').read_bytes()).hexdigest(),
        'control_sha256': hashlib.sha256((target / 'edge_control.png').read_bytes()).hexdigest(),
        'structure_preservation_verified': False,
        'next_step': 'Use edge_control.png with a compatible ControlNet checkpoint and compare same-seed images.',
    }
    (target / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return control, manifest
