"""Check the real child-worker runtime without loading SD1.5 weights."""
import json
import os
from pathlib import Path
import subprocess
import sys


def child_report(root):
    from app.cpu_readiness import inspect_local_assets
    root = Path(root)
    result = {
        'schema': 'bimai360.worker_runtime.v284',
        'worker_started': True,
        'torch_import': False,
        'diffusers_import': False,
        'cpu_supported': False,
        'cuda_supported': False,
        'model_ready': False,
        'inference_verified': False,
        'issues': [],
    }
    try:
        import torch
        result['torch_import'] = True
        result['cpu_supported'] = hasattr(torch, 'Generator') and hasattr(torch, 'float32')
        result['cuda_supported'] = bool(getattr(getattr(torch, 'version', None), 'cuda', None)) and bool(torch.cuda.is_available())
    except Exception as exc:
        result['issues'].append('TORCH_IMPORT_' + type(exc).__name__)
    try:
        from diffusers import AutoPipelineForImage2Image
        result['diffusers_import'] = True
    except Exception as exc:
        result['issues'].append('DIFFUSERS_IMPORT_' + type(exc).__name__)
    assets = inspect_local_assets(root)
    result['model_ready'] = bool(assets.get('model_files_complete'))
    if not result['model_ready']:
        result['issues'].append('MODEL_MISSING_OR_INCOMPLETE')
    return result


def parent_report(root, timeout=90):
    root = Path(root).resolve()
    if getattr(sys, 'frozen', False):
        command = [sys.executable, '--worker-runtime-child']
    else:
        command = [sys.executable, '-m', 'app.worker_runtime_report', '--child']
    process = subprocess.run(command, cwd=root, capture_output=True, text=True,
                             timeout=timeout, check=False)
    if process.returncode:
        raise RuntimeError('Worker runtime child exit code ' + str(process.returncode))
    result = json.loads(process.stdout.strip())
    if result.get('schema') != 'bimai360.worker_runtime.v284' or not result.get('worker_started'):
        raise RuntimeError('Worker runtime JSON contract invalid')
    log_dir = root / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / 'worker_runtime_v284.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    if sys.argv[1:] != ['--child']:
        raise SystemExit(2)
    root = Path(os.environ.get('BIMAI360_HOME') or Path.cwd())
    print(json.dumps(child_report(root), ensure_ascii=False))
