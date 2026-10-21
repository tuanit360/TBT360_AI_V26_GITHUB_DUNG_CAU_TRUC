"""Auditable opt-in continual-learning supervision, NOT unattended GPU training."""
from __future__ import annotations
import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def load_records(path):
    records = []
    with open(path, encoding='utf-8') as source:
        for line_num, line in enumerate(source, 1):
            if line.strip():
                try:
                    records.append(json.loads(line))
                except ValueError as exc:
                    raise ValueError(f'JSONL dòng {line_num} không hợp lệ') from exc
    return records


def dataset_audit(manifest, root, holdout_ratio=0.25):
    """One whole project per split; prevents same-project leakage and exact file duplication."""
    root = Path(root).resolve()
    rows = load_records(manifest)
    if not (0.1 <= holdout_ratio <= 0.5):
        raise ValueError('holdout_ratio phải nằm trong 0.1..0.5')
    by_project, by_digest, errors = defaultdict(list), {}, []
    allowed_disciplines = {'architecture', 'structure', 'mep', 'bim'}
    for idx, row in enumerate(rows):
        project = row.get('project_id')
        caption = row.get('caption')
        rel = row.get('file_name')
        if not isinstance(project, str) or not re.fullmatch(r'[A-Za-z0-9_-]{2,64}', project):
            errors.append({'index': idx, 'error': 'project_id invalid'}); continue
        if not isinstance(caption, str) or len(caption.strip()) < 12:
            errors.append({'index': idx, 'error': 'caption missing or too short'}); continue
        if row.get('discipline') not in allowed_disciplines:
            errors.append({'index': idx, 'error': 'discipline invalid'}); continue
        if row.get('verification') not in ('concept', 'geometry_validated', 'engineering_verified'):
            errors.append({'index': idx, 'error': 'verification invalid'}); continue
        if not isinstance(rel, str) or Path(rel).is_absolute():
            errors.append({'index': idx, 'error': 'unsafe file path'}); continue
        path = (root / rel).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            errors.append({'index': idx, 'error': 'missing/unsafe file'}); continue
        checksum = digest(path)
        if checksum in by_digest:
            errors.append({'index': idx, 'error': 'duplicate bytes', 'earlier_project': by_digest[checksum]})
            continue
        by_digest[checksum] = project
        by_project[project].append({'file_name': rel, 'caption': caption.strip(), 'sha256': checksum, 'discipline': row['discipline'], 'verification': row['verification']})
    projects = sorted(by_project)
    if len(projects) < 3:
        errors.append({'error': 'At least three distinct nonempty projects required for grouped holdout'})
    ordered = sorted(projects, key=lambda p: hashlib.sha256(('TBT360_holdout_v1:' + p).encode()).hexdigest())
    count = min(len(ordered) - 1, max(1, round(len(ordered) * holdout_ratio))) if ordered else 0
    val = set(ordered[:count]); train = set(ordered[count:])
    assert not val.intersection(train)
    output = {'status': 'PASS' if not errors else 'BLOCKED', 'train_projects': sorted(train),
              'validation_projects': sorted(val), 'train_images': sum(len(by_project[p]) for p in train),
              'validation_images': sum(len(by_project[p]) for p in val), 'errors': errors,
              'split_method': 'SHA256 project-id deterministic, disjoint project holdout',
              'records': {'train': [r for p in sorted(train) for r in by_project[p]],
                          'validation': [r for p in sorted(val) for r in by_project[p]]},
              'warning': 'Checks exact duplicates only. Human review needed for perceptual duplicates, license and labels.'}
    return output


def validate_bim(model):
    """Bounded 2D footprint checks; no claim of comprehensive IFC/engineering certification."""
    issues = []
    units = model.get('units')
    if units != 'm':
        issues.append('Units must be metres (m)')
    objects = model.get('entities', [])
    ids, walls, count = set(), {}, 0
    for entity in objects:
        count += 1
        eid, kind = entity.get('id'), entity.get('type')
        if not eid or eid in ids:
            issues.append(f'Duplicate/missing entity id: {eid}'); continue
        ids.add(eid)
        box = entity.get('bbox_m')
        if not isinstance(box, list) or len(box) != 4 or any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in box):
            issues.append(f'{eid}: invalid bbox'); continue
        x1, y1, x2, y2 = box
        if x1 >= x2 or y1 >= y2:
            issues.append(f'{eid}: nonpositive extent')
        if kind == 'wall':
            walls[eid] = entity
        if kind in ('door', 'window') and not entity.get('host_id'):
            issues.append(f'{eid}: no wall host')
        if entity.get('level_m') is not None and not isinstance(entity['level_m'], (int, float)):
            issues.append(f'{eid}: invalid level')
    for entity in objects:
        if entity.get('type') in ('door', 'window'):
            host = walls.get(entity.get('host_id'))
            if not host:
                issues.append(f"{entity.get('id')}: host wall absent")
                continue
            a = entity.get('bbox_m', []); b = host.get('bbox_m', [])
            if len(a) == 4 and len(b) == 4 and not (a[0] >= b[0] - .05 and a[2] <= b[2] + .05 and a[1] >= b[1] - .05 and a[3] <= b[3] + .05):
                issues.append(f"{entity.get('id')}: opening not contained in wall footprint")
    return {'status': 'PASS' if not issues else 'BLOCKED', 'entities': count, 'issues': issues,
            'scope': 'Bounded footprint/unit/identity/opening-host checks only, not IFC roundtrip or structural verification'}


def geometry_score(reference, candidate):
    """Scores canonical entity geometry; never infers meters from pixels."""
    def entities(model):
        return {e['id']: e for e in model['entities'] if 'id' in e and 'bbox_m' in e and len(e['bbox_m']) == 4}
    a, b = entities(reference), entities(candidate)
    common = a.keys() & b.keys()
    distances = []
    for entity_id in common:
        if a[entity_id].get('type') != b[entity_id].get('type'):
            continue
        distances.append(sum(abs(v - w) for v, w in zip(a[entity_id]['bbox_m'], b[entity_id]['bbox_m'])) / 4)
    mean_error = sum(distances) / len(distances) if distances else None
    return {'matched_entities': len(distances), 'reference_entities': len(a), 'candidate_entities': len(b),
            'mean_bbox_coordinate_error_m': round(mean_error, 6) if mean_error is not None else None,
            'entity_recall': round(len(distances)/len(a), 6) if a else None,
            'interpretation': 'Metric requires two models in same units/axes with matching IDs; image-only results cannot be scored this way'}


def compare_runs(before, after):
    """Requires identical evaluation inputs/seeds; does not fabricate generated imagery."""
    keys = ('model_input_sha256', 'seed', 'prompt', 'resolution', 'control_input_sha256')
    mismatch = [key for key in keys if before.get(key) != after.get(key)]
    if mismatch:
        return {'status': 'BLOCKED', 'mismatched_settings': mismatch}
    return {'status': 'COMPARABLE', 'same_input_seed': True,
            'before_metrics': before.get('metrics', {}), 'after_metrics': after.get('metrics', {}),
            'note': 'Comparison eligibility only; score image quality with verified annotations or blinded reviewers'}


def select_checkpoint(records, max_train_val_gap=0.15):
    """Checkpoint is eligible only with held-out metric and bounded generalization gap."""
    candidates, rejected = [], []
    for record in records:
        identifier = record.get('checkpoint')
        train, val = record.get('train_score'), record.get('validation_score')
        if not isinstance(identifier, str) or not isinstance(train, (int, float)) or not isinstance(val, (int, float)) or not all(math.isfinite(x) and 0 <= x <= 1 for x in (train, val)):
            rejected.append({'checkpoint': identifier, 'reason': 'missing/invalid measured scores'}); continue
        gap = train - val
        if gap > max_train_val_gap:
            rejected.append({'checkpoint': identifier, 'reason': 'overfit flag', 'gap': round(gap, 5)}); continue
        candidates.append((val, -abs(gap), identifier))
    candidates.sort(reverse=True)
    return {'selected': candidates[0][2] if candidates else None, 'rejected': rejected,
            'policy': 'Maximize held-out validation score, disqualify excessive train/validation gap',
            'warning': 'Scores must be from actual evaluation; no synthetic scores may certify weights'}


def append_feedback(path, item):
    """Records append-only human judgments; DOES NOT train automatically."""
    required = ('output_sha256', 'project_id', 'rating', 'consent', 'comment')
    if any(k not in item for k in required):
        raise ValueError('Feedback fields missing')
    if not re.fullmatch(r'[a-f0-9]{64}', str(item['output_sha256'])):
        raise ValueError('Invalid image checksum')
    if not re.fullmatch(r'[A-Za-z0-9_-]{2,64}', str(item['project_id'])):
        raise ValueError('Invalid project')
    if type(item['rating']) is not int or item['rating'] not in (1, 2, 3, 4, 5):
        raise ValueError('Rating must be 1..5')
    if item['consent'] is not True:
        raise ValueError('Explicit opt-in consent required')
    if not isinstance(item['comment'], str) or len(item['comment']) > 1000:
        raise ValueError('Invalid comment')
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    record = {'time_utc': datetime.now(timezone.utc).isoformat(), 'status': 'PENDING_HUMAN_REVIEW', **item}
    with path.open('a', encoding='utf-8') as destination:
        destination.write(json.dumps(record, ensure_ascii=False) + '\n')
    return record
