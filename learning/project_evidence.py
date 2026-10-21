"""V70 project-aware, reproducible evidence gate. No imaginary model weights or GPU results."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
from learning.core import validate_bim, geometry_score, write_json


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(block)
    return hasher.hexdigest()


def evaluate_project_bundle(manifest_path, project_root):
    """Verify annotated 2D/image/3D file links and bounded canonical geometry."""
    root = Path(project_root).resolve()
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    problems, checked, by_project = [], [], {}
    if manifest.get('schema_version') != 'tbt360-v70-project-evidence-v1':
        problems.append('Invalid manifest schema_version')
    projects = manifest.get('projects', [])
    if not isinstance(projects, list) or not projects:
        return {'status': 'BLOCKED', 'issues': problems + ['No projects provided'], 'items': []}
    for project in projects:
        pid = project.get('project_id')
        if not isinstance(pid, str) or not pid or pid in by_project:
            problems.append('Missing or repeated project_id')
            continue
        by_project[pid] = True
        assets = project.get('assets', [])
        if not isinstance(assets, list) or not assets:
            problems.append(f'{pid}: no assets')
            continue
        canonical_models = {}
        used_ids = set()
        for asset in assets:
            aid, kind, rel = asset.get('asset_id'), asset.get('kind'), asset.get('path')
            if not aid or aid in used_ids:
                problems.append(f'{pid}: missing/duplicate asset id')
                continue
            used_ids.add(aid)
            if kind not in {'render', 'floorplan', 'elevation', 'section', 'bim_json'}:
                problems.append(f'{pid}/{aid}: unknown asset type')
                continue
            if not isinstance(rel, str) or not rel:
                problems.append(f'{pid}/{aid}: missing path')
                continue
            file_path = (root / rel).resolve()
            if not file_path.is_relative_to(root) or not file_path.is_file():
                problems.append(f'{pid}/{aid}: missing or unsafe file')
                continue
            expected = asset.get('sha256')
            actual = _sha256(file_path)
            if expected != actual:
                problems.append(f'{pid}/{aid}: checksum mismatch')
                continue
            verification = asset.get('verification')
            if verification not in {'concept', 'geometry_validated', 'engineering_verified'}:
                problems.append(f'{pid}/{aid}: verification required')
            if kind == 'bim_json':
                try:
                    model = json.loads(file_path.read_text(encoding='utf-8'))
                    result = validate_bim(model)
                    canonical_models[aid] = model
                    if result['status'] != 'PASS':
                        problems.append(f'{pid}/{aid}: BIM invalid: {result["issues"]}')
                except (ValueError, TypeError, KeyError) as exc:
                    problems.append(f'{pid}/{aid}: BIM parse error: {exc}')
            checked.append({'project_id': pid, 'asset_id': aid, 'kind': kind, 'sha256': actual, 'verification': verification})
        for asset in assets:
            if asset.get('kind') != 'bim_json':
                ref = asset.get('canonical_asset_id')
                if not ref or ref not in canonical_models:
                    problems.append(f'{pid}/{asset.get("asset_id")}: absent canonical BIM mapping')
        if not any(asset.get('kind') == 'floorplan' for asset in assets):
            problems.append(f'{pid}: missing floorplan')
        if not any(asset.get('kind') == 'render' for asset in assets):
            problems.append(f'{pid}: missing render')
    return {'status': 'PASS' if not problems else 'BLOCKED', 'issues': problems,
            'items': checked, 'project_count': len(by_project),
            'scope': 'Asset linkage, checksums and bounded BIM JSON checks only. Does NOT verify pixels match BIM.'}


def evaluate_checkpoint_trials(trials, min_projects=2, max_drop=0.03):
    """Use independent held-out project scores; never invent a trained result."""
    errors = []
    by_candidate = {}
    for record in trials:
        name, project, score = record.get('checkpoint'), record.get('project_id'), record.get('score')
        if not isinstance(name, str) or not name or not isinstance(project, str) or not project:
            errors.append('checkpoint/project_id invalid')
            continue
        if type(score) not in (float, int) or not math.isfinite(score) or not 0 <= score <= 1:
            errors.append(f'{name}/{project}: score must be finite 0..1')
            continue
        group = by_candidate.setdefault(name, {})
        if project in group:
            errors.append(f'{name}/{project}: duplicate trial')
        group[project] = score
    if len(by_candidate) < 2:
        errors.append('Require baseline and candidate')
    names = sorted(by_candidate)
    if not names:
        return {'status': 'BLOCKED', 'issues': errors}
    baseline = 'baseline'
    if baseline not in by_candidate:
        errors.append('Missing baseline checkpoint')
        return {'status': 'BLOCKED', 'issues': errors}
    reference_projects = set(by_candidate[baseline])
    if len(reference_projects) < min_projects:
        errors.append(f'At least {min_projects} held-out projects required')
    summary = {}
    for checkpoint, scores in by_candidate.items():
        if set(scores) != reference_projects:
            errors.append(f'{checkpoint}: incomplete/unmatched project set')
            continue
        deltas = [scores[p] - by_candidate[baseline][p] for p in sorted(reference_projects)]
        mean = sum(scores.values()) / len(scores)
        drop = min(deltas)
        eligible = checkpoint == baseline or (sum(deltas) > 0 and drop >= -max_drop)
        summary[checkpoint] = {'mean_score': round(mean, 6), 'min_project_delta': round(drop, 6), 'eligible': eligible}
    candidates = [(values['mean_score'], name) for name, values in summary.items() if name != baseline and values['eligible']]
    selected = max(candidates)[1] if candidates and not errors else None
    return {'status': 'BLOCKED' if errors else ('PROMOTION_RECOMMENDED' if selected else 'KEEP_BASELINE'),
            'selected': selected, 'issues': errors, 'summary': summary,
            'scope': 'Gate uses externally measured scores on actual held-out projects. It does not compute visual/BIM fidelity itself.'}


def draft_promotion(evaluation, current_checkpoint_sha256, candidate_checkpoint_sha256):
    """Create review document only, never modify runtime or model weights."""
    for checksum in (current_checkpoint_sha256, candidate_checkpoint_sha256):
        if not isinstance(checksum, str) or len(checksum) != 64 or any(c not in '0123456789abcdef' for c in checksum):
            raise ValueError('Expected lowercase sha256 for both checkpoints')
    if evaluation.get('status') != 'PROMOTION_RECOMMENDED':
        raise ValueError('Candidate has not passed promotion evaluation')
    return {'status': 'PENDING_HUMAN_APPROVAL', 'candidate': evaluation['selected'],
            'current_sha256': current_checkpoint_sha256, 'candidate_sha256': candidate_checkpoint_sha256,
            'rollback_sha256': current_checkpoint_sha256,
            'warning': 'Review-only artifact. No automatic training, model swap or deployment.'}
