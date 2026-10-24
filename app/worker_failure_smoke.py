"""Exercise the actual frozen worker failure path, without a model or GPU."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def run_failure_contract(root, timeout=90):
    root = Path(root).resolve()
    with tempfile.TemporaryDirectory(prefix='bimai360_failure_') as directory:
        job_dir = Path(directory)
        job_file = job_dir / 'job.json'
        # Invalid schema must fail before importing PyTorch or Diffusers.
        job_file.write_text(json.dumps({'schema': 'intentional_invalid_smoke'}), encoding='utf-8')
        if getattr(sys, 'frozen', False):
            command = [sys.executable, '--worker-image', '--job', str(job_file)]
        else:
            command = [sys.executable, '-m', 'app.isolated_image_worker',
                       '--job', str(job_file)]
        result = subprocess.run(command, cwd=root, capture_output=True,
                                text=True, timeout=timeout, check=False)
        from app.worker_failure import read_safe_worker_failure
        error_file = job_dir / 'worker_failure.json'
        if result.returncode == 0 or not error_file.is_file():
            raise RuntimeError('Worker failure was not isolated or not reported')
        report = json.loads(error_file.read_text(encoding='utf-8'))
        if report.get('schema') != 'bimai360.worker_failure.v1':
            raise RuntimeError('Invalid worker failure schema')
        if report.get('status') != 'FAILED':
            raise RuntimeError('Worker failure was not recorded')
        safe_message = read_safe_worker_failure(error_file)
        if not safe_message:
            raise RuntimeError('No safe user-facing failure message')
        return {'status': 'PASS_FAILURE_CONTRACT_ONLY',
                'worker_exit': result.returncode,
                'failure_code': report.get('code'),
                'safe_message': safe_message,
                'real_ai_inference_verified': False}
