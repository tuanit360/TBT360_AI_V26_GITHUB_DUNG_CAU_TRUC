"""V75: independent metric-geometry annotation gate, NOT image-to-BIM prediction."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

from evaluation.bim_plan import validate_model

SCHEMA = 'tbt360-v75-metric-bim-evidence-v1'
KINDS = {'wall', 'door', 'window', 'column', 'beam', 'slab', 'room', 'roof'}


def _boxes(items):
    return {item['id']: item for item in items}


def _geometry_error(model, annotations):
    valid = validate_model(model)
    if not isinstance(annotations, dict) or annotations.get('units') != 'm':
        raise ValueError('Independent annotations must use metres')
    objects = annotations.get('entities')
    if not isinstance(objects, list) or not objects:
        raise ValueError('Independent annotations required')
    actual = {}
    for item in objects:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id'] or item['id'] in actual:
            raise ValueError('Duplicate or invalid annotation id')
        box = item.get('bbox_m')
        if item.get('type') not in KINDS or not isinstance(box, list) or len(box) != 4 or any(type(x) not in (int, float) or not math.isfinite(x) for x in box) or box[2] <= box[0] or box[3] <= box[1]:
            raise ValueError('Invalid annotation box/type')
        actual[item['id']] = item
    if set(valid) != set(actual):
        raise ValueError('Missing or extra entity annotations')
    errors = []
    by_class = {}
    for key, ref in actual.items():
        predicted = valid[key]
        if predicted['type'] != ref['type']:
            raise ValueError('Annotation class mismatch')
        if predicted['type'] in ('door','window') and ref.get('host_id') != predicted.get('host_id'):
            raise ValueError('Host relationship mismatch')
        pb, rb = predicted['bbox_m'], ref['bbox_m']
        delta = [abs(a-b) for a,b in zip(pb,rb)]
        errors.extend(delta)
        by_class.setdefault(ref['type'], []).extend(delta)
    return {
        'max_coordinate_error_m': round(max(errors), 8),
        'mean_coordinate_error_m': round(sum(errors)/len(errors), 8),
        'by_class_max_coordinate_error_m': {k: round(max(v), 8) for k,v in sorted(by_class.items())},
        'entities': len(valid),
    }


def _load_asset(root, item):
    if not isinstance(item, dict) or not isinstance(item.get('path'), str) or not isinstance(item.get('sha256'), str):
        raise ValueError('Asset path and SHA256 required')
    path = (root/item['path']).resolve()
    if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
        raise ValueError('Unsafe asset path')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != item['sha256']:
        raise ValueError('Asset SHA256 mismatch')
    return json.loads(data)


def evaluate(manifest_path, root, max_error_m=0.02):
    if not math.isfinite(max_error_m) or max_error_m < 0:
        raise ValueError('Tolerance must be finite and nonnegative')
    root = Path(root).resolve()
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    if manifest.get('schema_version') != SCHEMA:
        raise ValueError('Unsupported manifest version')
    train = set(manifest.get('train_project_ids', []))
    validation = set(manifest.get('validation_project_ids', []))
    if len(validation) < 2 or train & validation:
        raise ValueError('Need 2+ disjoint holdout projects')
    cases = manifest.get('cases', [])
    if not isinstance(cases, list) or not cases:
        raise ValueError('Nonempty cases required')
    seen, results = set(), []
    for case in cases:
        project = case.get('project_id')
        if project not in validation or project in seen:
            raise ValueError('Each validation project needs exactly one independent annotation pair')
        seen.add(project)
        predicted = _load_asset(root, case.get('predicted_bim'))
        labeled = _load_asset(root, case.get('independent_annotation'))
        result = _geometry_error(predicted, labeled)
        result['project_id'] = project
        result['pass'] = result['max_coordinate_error_m'] <= max_error_m
        results.append(result)
    if seen != validation:
        raise ValueError('All holdout projects must be evaluated')
    mean = sum(v['mean_coordinate_error_m'] for v in results)/len(results)
    return {'schema_version': SCHEMA, 'status': 'METRIC_GATE_PASS' if all(v['pass'] for v in results) else 'METRIC_GATE_FAIL',
            'max_allowed_error_m': max_error_m, 'mean_project_error_m': round(mean, 8), 'projects': results,
            'limitations': 'Compares provided BIM JSON coordinates against separately authored BIM annotations. Does not extract BIM from images, certify construction dimensions, or demonstrate AI learning.'}


def main():
    p = argparse.ArgumentParser(description='Evaluate BIM JSON vs independent metric annotations')
    p.add_argument('manifest', type=Path)
    p.add_argument('--assets', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--tolerance-m', type=float, default=0.02)
    a = p.parse_args()
    result = evaluate(a.manifest, a.assets, a.tolerance_m)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'status': result['status'], 'projects': len(result['projects'])}))
    if result['status'] != 'METRIC_GATE_PASS':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
