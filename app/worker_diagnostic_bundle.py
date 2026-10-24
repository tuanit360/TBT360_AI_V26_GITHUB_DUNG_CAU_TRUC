"""Offline, privacy-redacted diagnostic ZIP for worker failures."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import zipfile

from app.diagnostic_bundle import redact, MAX_LOG_BYTES
from app.worker_evidence import read_report

SAFE_LOGS = (
    'image_worker.log', 'generation_stage.log',
    'runtime_errors.log', 'startup_console.log', 'python_fatal.log',
)


def make_worker_bundle(root, *, job_id=None):
    root = Path(root).resolve()
    logs = root / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    report = read_report(root)
    if job_id is not None and report.get('job_id') != job_id:
        report = {'status': 'JOB_MISMATCH'}
    destination = logs / 'last_failure_bundle.zip'
    temporary = destination.with_name(destination.name + '.tmp')
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                'last_worker_state.json',
                json.dumps(report, ensure_ascii=True, indent=2),
            )
            for filename in SAFE_LOGS:
                file = logs / filename
                if not file.is_file() or file.is_symlink():
                    continue
                with file.open('rb') as handle:
                    handle.seek(max(0, file.stat().st_size - MAX_LOG_BYTES))
                    text = handle.read(MAX_LOG_BYTES).decode(
                        'utf-8', errors='replace'
                    )
                archive.writestr(
                    'logs/' + filename,
                    redact(text),
                )
            archive.writestr('README.txt',
                'Review all contents before sharing. '
                'No image/model/project files included.')
        with zipfile.ZipFile(temporary) as test:
            if test.testzip() is not None:
                raise ValueError('Diagnostic ZIP verification failed')
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return str(destination)
