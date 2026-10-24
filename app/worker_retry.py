"""Conservative CPU retry policy."""
import json
from pathlib import Path


def should_retry_cpu(path, environment):
    if environment.get('BIMAI360_FORCE_CPU') == '1':
        return False
    try:
        path = Path(path)
        if path.stat().st_size > 2048:
            return False
        value = json.loads(path.read_text(encoding='utf-8'))
        return (
            value.get('schema') == 'bimai360.worker_failure.v1'
            and value.get('status') == 'FAILED'
            and value.get('code') == 'CUDA_UNAVAILABLE'
        )
    except (OSError, ValueError, TypeError):
        return False
