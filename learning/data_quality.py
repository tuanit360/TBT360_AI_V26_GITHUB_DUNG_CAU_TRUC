"""V71 opt-in training data gate: real image bytes, provenance, project isolation.

No ML weights are trained here; tests use synthetic fixtures and must not be
presented as real-world accuracy evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _sha256(path):
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def _dhash(img):
    from PIL import Image
    thumb = img.convert('L').resize((9, 8), Image.Resampling.LANCZOS)
    pixels = list(thumb.get_flattened_data() if hasattr(thumb, 'get_flattened_data') else thumb.getdata())
    return sum((1 << (row * 8 + col)) for row in range(8) for col in range(8)
               if pixels[row * 9 + col] > pixels[row * 9 + col + 1])


def inspect_training_manifest(manifest_path, image_root, *, holdout_ratio=0.2,
                              min_projects=3, near_duplicate_distance=4):
    """Validate a JSONL manifest. Fail closed, do not export train lists on errors.

    Required: project_id, file_name, sha256, caption, discipline, verification,
    label_classes, license, consent_to_train, source.
    """
    if not 0 < holdout_ratio < 1:
        raise ValueError('holdout_ratio must be between zero and one')
    root = Path(image_root).resolve()
    issues, accepted = [], []
    known_digest = {}
    valid_disciplines = {'architecture', 'structure', 'mep', 'bim'}
    valid_verification = {'concept', 'geometry_validated', 'engineering_verified'}
    rows = Path(manifest_path).read_text(encoding='utf-8').splitlines()
    for number, line in enumerate(rows, 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError('record is not an object')
        except ValueError as exc:
            issues.append(f'line {number}: malformed JSON: {exc}')
            continue
        project = item.get('project_id')
        relative = item.get('file_name')
        if not isinstance(project, str) or not project.strip() or not isinstance(relative, str):
            issues.append(f'line {number}: missing project ID or file_name')
            continue
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            issues.append(f'line {number}: missing or unsafe image path')
            continue
        if item.get('discipline') not in valid_disciplines or item.get('verification') not in valid_verification:
            issues.append(f'line {number}: invalid discipline/verification')
            continue
        if not isinstance(item.get('caption'), str) or len(item['caption'].strip()) < 12:
            issues.append(f'line {number}: missing useful caption')
            continue
        labels = item.get('label_classes')
        if not isinstance(labels, list) or not labels or any(not isinstance(v, str) or not v.strip() for v in labels):
            issues.append(f'line {number}: missing class labels')
            continue
        if not item.get('license') or not item.get('source') or item.get('consent_to_train') is not True:
            issues.append(f'line {number}: source/license/training permission required')
            continue
        digest = _sha256(path)
        if digest != item.get('sha256'):
            issues.append(f'line {number}: SHA256 mismatch')
            continue
        if digest in known_digest:
            issues.append(f'line {number}: duplicate bytes of line {known_digest[digest]}')
            continue
        known_digest[digest] = number
        try:
            from PIL import Image, UnidentifiedImageError
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                width, height = image.size
                if width < 256 or height < 256:
                    issues.append(f'line {number}: image smaller than 256px')
                    continue
                perceptual = _dhash(image)
        except (OSError, ValueError) as exc:
            issues.append(f'line {number}: unreadable image: {exc}')
            continue
        accepted.append({'line': number, 'project_id': project, 'file_name': relative,
                         'sha256': digest, 'dhash': perceptual, 'width': width, 'height': height})
    project_ids = sorted({entry['project_id'] for entry in accepted})
    if len(project_ids) < min_projects:
        issues.append(f'require at least {min_projects} distinct projects')
    ordered = sorted(project_ids, key=lambda p: hashlib.sha256(f'v71-heldout:{p}'.encode()).hexdigest())
    n_holdout = max(1, min(len(ordered) - 1, round(len(ordered) * holdout_ratio))) if len(ordered) > 1 else 0
    validation = set(ordered[:n_holdout])
    train = set(ordered[n_holdout:])
    near_pairs = []
    # Audit near duplicates across projects even within the same split: future
    # resplitting must not accidentally leak these across evaluation boundaries.
    for idx, left in enumerate(accepted):
        for right in accepted[idx + 1:]:
            if left['project_id'] == right['project_id']:
                continue
            distance = (left['dhash'] ^ right['dhash']).bit_count()
            if distance <= near_duplicate_distance:
                near_pairs.append({'left_line': left['line'], 'right_line': right['line'],
                                   'distance': distance, 'cross_split': (left['project_id'] in validation) != (right['project_id'] in validation)})
    if near_pairs:
        issues.append(f'{len(near_pairs)} near-duplicate image pairs across projects; human review required')
    summary = {
        'status': 'PASS' if not issues else 'BLOCKED',
        'images_checked': len(accepted), 'projects_checked': len(project_ids),
        'train_projects': sorted(train), 'validation_projects': sorted(validation),
        'near_duplicate_pairs': near_pairs[:100], 'issues': issues,
        'scope': 'Image decoding, provenance fields, source permission assertion, duplicate detection and deterministic project split. Not an authenticity, label correctness or image/BIM fidelity certificate.',
    }
    if summary['status'] == 'PASS':
        summary['train_files'] = [a['file_name'] for a in accepted if a['project_id'] in train]
        summary['validation_files'] = [a['file_name'] for a in accepted if a['project_id'] in validation]
    return summary


def main():
    parser = argparse.ArgumentParser(description='Fail-closed training data audit')
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--root', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    outcome = inspect_training_manifest(args.manifest, args.root)
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(outcome, ensure_ascii=False, indent=2), encoding='utf-8')
    print(outcome['status'], len(outcome['issues']), 'issue(s)')
    return 0 if outcome['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
