"""Auditable image-leakage check for project-held-out machine learning data.

This does not train or certify a model. The split must be generated from
reviewed project IDs by learning.core.dataset_audit first.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageOps

from learning.core import dataset_audit, write_json

IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp'}


def image_fingerprint(path: Path):
    with Image.open(path) as source:
        rgb = ImageOps.exif_transpose(source).convert('RGB')
        rgb.load()
        pixel_hash = hashlib.sha256(rgb.tobytes()).hexdigest()
        gray = rgb.resize((9, 8), Image.Resampling.LANCZOS).convert('L')
        values = list(gray.getdata())
        difference_hash = sum(
            1 << (row * 8 + column)
            for row in range(8)
            for column in range(8)
            if values[row * 9 + column] > values[row * 9 + column + 1]
        )
        return pixel_hash, difference_hash


def check_training_leakage(manifest: Path, root: Path):
    root = Path(root).resolve()
    split = dataset_audit(manifest, root)
    result = {
        'schema': 'bimai360.training_leakage.v1',
        'status': 'BLOCKED',
        'grouped_split_status': split['status'],
        'train_projects': split['train_projects'],
        'validation_projects': split['validation_projects'],
        'cross_split_pixel_duplicates': [],
        'cross_split_near_duplicates': [],
        'errors': list(split['errors']),
        'note': (
            'A PASS checks split separation only, not labels, image licenses, '
            'training quality, or actual LoRA learning.'
        ),
    }
    if split['status'] != 'PASS':
        return result
    train = []
    validation = []
    for group, collection in (
        ('train', train),
        ('validation', validation),
    ):
        for record in split['records'][group]:
            name = record['file_name']
            if Path(name).suffix.lower() not in IMAGE_SUFFIXES:
                continue
            try:
                pixel_hash, difference_hash = image_fingerprint(root / name)
            except (OSError, ValueError) as exc:
                result['errors'].append({
                    'file': name,
                    'reason': type(exc).__name__,
                })
                continue
            collection.append((name, pixel_hash, difference_hash))
    for name, pixel_hash, difference_hash in train:
        for other_name, other_hash, other_difference in validation:
            if pixel_hash == other_hash:
                result['cross_split_pixel_duplicates'].append([name, other_name])
            elif (difference_hash ^ other_difference).bit_count() <= 5:
                result['cross_split_near_duplicates'].append([name, other_name])
    if result['cross_split_pixel_duplicates']:
        result['errors'].append('Same image pixels present in train and validation')
    if result['cross_split_near_duplicates']:
        result['errors'].append('Potential visual duplicates across held-out projects require human review')
    if not result['errors']:
        result['status'] = 'SPLIT_VALID_NOT_TRAINED'
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = check_training_leakage(args.manifest, args.root)
    write_json(args.out, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['status'] == 'SPLIT_VALID_NOT_TRAINED' else 2)


if __name__ == '__main__':
    main()
