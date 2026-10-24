"""Small, redacted, atomic evidence for the most recent isolated job."""
import json
import os
from pathlib import Path
from datetime import datetime, timezone


def write_state(root, job_id, stage, status='RUNNING', code=''):
    root = Path(root)
    if not (isinstance(job_id, str) and len(job_id) == 16
            and all(char in '0123456789abcdef' for char in job_id)):
        return
    if stage not in {
        'BOOT', 'TORCH_IMPORT_BEGIN', 'TORCH_IMPORT_DONE',
        'DIFFUSERS_IMPORT_BEGIN', 'DIFFUSERS_IMPORT_DONE',
        'MODEL_LOAD_BEGIN', 'MODEL_LOAD_DONE', 'INFERENCE_BEGIN',
        'INFERENCE_DONE', 'PNG_SAVE_BEGIN', 'PNG_SAVE_DONE',
        'ZIP_EXPORT_BEGIN', 'ZIP_EXPORT_DONE', 'DONE', 'FAILED',
    }:
        return
    target = root / 'logs' / 'last_worker_state.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'schema': 'bimai360.worker_evidence.v289',
        'job_id': job_id, 'stage': stage,
        'status': status, 'code': str(code)[:40],
        'utc': datetime.now(timezone.utc).isoformat(),
    }
    temp = target.with_name(target.name + '.' + job_id + '.tmp')
    temp.write_text(json.dumps(payload, ensure_ascii=True), encoding='utf-8')
    os.replace(temp, target)


def read_report(root):
    target = Path(root) / 'logs' / 'last_worker_state.json'
    try:
        if target.stat().st_size > 4096:
            return {'status': 'INVALID'}
        data = json.loads(target.read_text(encoding='utf-8'))
        if data.get('schema') != 'bimai360.worker_evidence.v289':
            return {'status': 'INVALID'}
        return {key: data.get(key) for key in
                ('schema', 'job_id', 'stage', 'status', 'code', 'utc')}
    except (OSError, ValueError, TypeError):
        return {'status': 'NO_REPORT'}
