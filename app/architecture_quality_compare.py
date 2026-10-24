"""V85 reproducible architecture image comparison and quality diagnostics.

Pixel comparisons are descriptive only; they do not certify architectural
geometry, BIM correctness, or LoRA improvement.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageOps, ImageStat, ImageFilter


def compare_images(reference, candidate, seed=42):
    if not isinstance(reference, Image.Image) or not isinstance(candidate, Image.Image):
        raise ValueError('Cần đủ ảnh gốc và ảnh kết quả')
    first = ImageOps.exif_transpose(reference).convert('RGB')
    second = ImageOps.exif_transpose(candidate).convert('RGB')
    if min(first.size + second.size) < 64:
        raise ValueError('Ảnh quá nhỏ để kiểm tra')
    resized = second.resize(first.size, Image.Resampling.LANCZOS)
    difference = ImageChops.difference(first, resized)
    grayscale = difference.convert('L')
    difference_mean = ImageStat.Stat(grayscale).mean[0]
    reference_edges = first.convert('L').filter(ImageFilter.FIND_EDGES)
    result_edges = resized.convert('L').filter(ImageFilter.FIND_EDGES)
    edge_difference = ImageStat.Stat(ImageChops.difference(reference_edges, result_edges)).mean[0]
    side_by_side = Image.new('RGB', (first.width * 2, first.height))
    side_by_side.paste(first, (0, 0))
    side_by_side.paste(resized, (first.width, 0))
    return side_by_side, {
        'schema': 'tbt360.architecture_comparison.v85',
        'seed_user_supplied': int(seed),
        'reference_size_px': list(first.size),
        'candidate_original_size_px': list(second.size),
        'mean_pixel_difference_0_255': round(difference_mean, 3),
        'mean_edge_difference_0_255': round(edge_difference, 3),
        'note': 'These differences are descriptive; not a realism, BIM or geometry accuracy score.',
        'same_seed_generation_verified': False,
        'human_review_required': True,
    }


def export_comparison(reference, candidate, root, seed=42):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    composite, metrics = compare_images(reference, candidate, seed)
    composite.save(root / 'before_after.png')
    reference.convert('RGB').save(root / 'reference.png')
    candidate.convert('RGB').save(root / 'candidate.png')
    metrics['files_sha256'] = {
        item.name: hashlib.sha256(item.read_bytes()).hexdigest()
        for item in root.glob('*.png')
    }
    (root / 'comparison.json').write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding='utf-8')
    return composite, metrics
