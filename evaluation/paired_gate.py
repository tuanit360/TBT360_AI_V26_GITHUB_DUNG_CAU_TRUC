"""V73: evidence-only paired visual geometry gate. Never claims BIM semantic accuracy."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
from PIL import Image

SCHEMA = 'tbt360-v73-paired-geometry-v1'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def secure_asset(root, asset):
    if not isinstance(asset, dict) or not isinstance(asset.get('path'), str):
        raise ValueError('Asset must specify path and sha256')
    path = (root / asset['path']).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('Unsafe or missing asset')
    expected = asset.get('sha256')
    if not isinstance(expected, str) or len(expected) != 64 or digest(path) != expected:
        raise ValueError('Asset SHA256 mismatch')
    return path


def binary_mask(path):
    with Image.open(path) as source:
        if source.mode not in ('L', '1'):
            raise ValueError('Geometry mask must be grayscale L or binary 1')
        pixels = list(source.convert('L').getdata())
        if any(value not in (0, 255) for value in pixels):
            raise ValueError('Mask must contain only black/white pixels')
        return source.size, [value == 255 for value in pixels]


def overlap(predicted, truth):
    if predicted[0] != truth[0]:
        raise ValueError('Mask dimensions differ; no implicit resize allowed')
    a, b = predicted[1], truth[1]
    intersect = sum(x and y for x, y in zip(a, b))
    union = sum(x or y for x, y in zip(a, b))
    return 1.0 if not union else intersect / union


def evaluate(manifest_path, asset_root, min_projects=2, max_project_drop=0.03):
    root = Path(asset_root).resolve()
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    if manifest.get('schema_version') != SCHEMA:
        raise ValueError('Unsupported manifest schema')
    cases = manifest.get('cases')
    if not isinstance(cases, list) or not cases:
        raise ValueError('At least one evaluation case required')
    holdouts = set(manifest.get('validation_project_ids', []))
    train = set(manifest.get('train_project_ids', []))
    if not holdouts or train & holdouts:
        raise ValueError('Validation projects missing or overlapping train')
    if len(holdouts) < min_projects:
        raise ValueError('Not enough distinct validation projects')
    if not isinstance(manifest.get('checkpoint_baseline_sha256'), str) or not isinstance(manifest.get('checkpoint_candidate_sha256'), str):
        raise ValueError('Checkpoint hashes required')
    for name in ('checkpoint_baseline_sha256', 'checkpoint_candidate_sha256'):
        value = manifest[name]
        if len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('Invalid checkpoint SHA256')
    if manifest['checkpoint_baseline_sha256'] == manifest['checkpoint_candidate_sha256']:
        raise ValueError('Candidate and baseline checkpoints are identical')
    result_cases, by_project, seen = [], {}, set()
    for case in cases:
        project = case.get('project_id')
        case_id = case.get('case_id')
        if project not in holdouts or not case_id or (project, case_id) in seen:
            raise ValueError('Unknown holdout or duplicate case')
        seen.add((project, case_id))
        base = case.get('baseline', {})
        cand = case.get('candidate', {})
        for key in ('seed', 'prompt', 'negative_prompt', 'settings', 'input_sha256'):
            if base.get(key) is None or base.get(key) != cand.get(key):
                raise ValueError(f'Unpaired setting: {key}')
        if type(base['seed']) is not int or not isinstance(base['prompt'], str) or not base['prompt']:
            raise ValueError('Invalid seed/prompt')
        if not isinstance(base['settings'], dict) or not base['settings']:
            raise ValueError('Generation settings required')
        input_path = secure_asset(root, case.get('input_image'))
        if digest(input_path) != base['input_sha256']:
            raise ValueError('Input image checksum does not match paired parameters')
        ref = binary_mask(secure_asset(root, case.get('reference_geometry_mask')))
        old_path = secure_asset(root, base.get('image'))
        new_path = secure_asset(root, cand.get('image'))
        if digest(old_path) == digest(new_path):
            raise ValueError('Identical outputs cannot establish improvement')
        with Image.open(old_path) as old_image, Image.open(new_path) as new_image:
            if old_image.size != new_image.size or old_image.size != ref[0]:
                raise ValueError('Comparison images and masks must share pixel dimensions')
        old = overlap(binary_mask(secure_asset(root, base.get('geometry_mask'))), ref)
        new = overlap(binary_mask(secure_asset(root, cand.get('geometry_mask'))), ref)
        by_project.setdefault(project, []).append((old, new))
        result_cases.append({'project_id': project, 'case_id': case_id, 'seed': base['seed'],
                             'baseline_iou': round(old, 6), 'candidate_iou': round(new, 6),
                             'delta_iou': round(new-old, 6)})
    if set(by_project) != holdouts:
        raise ValueError('Each holdout project needs at least one case')
    project_scores = {}
    for project, measurements in sorted(by_project.items()):
        b = sum(item[0] for item in measurements) / len(measurements)
        c = sum(item[1] for item in measurements) / len(measurements)
        project_scores[project] = {'baseline_mean_iou': round(b, 6), 'candidate_mean_iou': round(c, 6),
                                   'delta_iou': round(c-b, 6), 'cases': len(measurements)}
    deltas = [v['delta_iou'] for v in project_scores.values()]
    passed = sum(deltas)/len(deltas) > 0 and min(deltas) >= -max_project_drop
    return {'schema_version': SCHEMA, 'status': 'REVIEW_CANDIDATE' if passed else 'KEEP_BASELINE',
            'requires_human_approval': True, 'projects': project_scores, 'cases': result_cases,
            'baseline_checkpoint_sha256': manifest['checkpoint_baseline_sha256'],
            'candidate_checkpoint_sha256': manifest['checkpoint_candidate_sha256'],
            'metric': 'binary annotated silhouette mask IoU',
            'limitations': 'Only measures supplied binary masks against annotated reference masks. Masks are not inferred by AI. It does not verify dimensions in metres, BIM semantics, photorealism, or engineering correctness.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = evaluate(args.manifest, args.assets)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': report['status'], 'projects': len(report['projects']), 'report': str(args.output)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
