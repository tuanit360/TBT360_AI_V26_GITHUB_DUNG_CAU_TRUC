"""Offline diagnostic ZIP, available even when Gradio callbacks or tabs fail.

Run via BIMAI360.exe --diagnostics; never includes model weights, images,
datasets, user files, tokens, raw environment variables or absolute paths.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import platform
import re
import sys
import zipfile

MAX_LOG_BYTES = 512 * 1024
ALLOWED_LOGS = ('bimai360_operations.log', 'startup_error.log', 'runtime_errors.log', 'console_errors.log')
SECRET = re.compile(
    r'(?i)(bearer\s+\S+|(?:token|api[_-]?key|password|secret)\s*[:=]\s*\S+)'
)
PATH = re.compile(r'(?:[A-Za-z]:\\[^\s"\']+|/home/[^\s"\']+|/Users/[^\s"\']+)')

def redact(value):
    value = SECRET.sub('[REDACTED_SECRET]', value)
    return PATH.sub('[REDACTED_PATH]', value)

def build_diagnostic_zip(root):
    root = Path(root).resolve()
    logs = root / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    archive = logs / ('BIMAI360_V271_DIAGNOSTICS_'
                      + datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f') + '.zip')
    summary = {
        'schema': 'bimai360.diagnostics.v1',
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'version': 'V271',
        'platform': platform.system(),
        'python_version': platform.python_version(),
        'frozen': bool(getattr(sys, 'frozen', False)),
        'offline': os.environ.get('TBT360_OFFLINE') == '1',
        'local_sd15_index_present': (root / 'models' / 'sd15' / 'model_index.json').is_file(),
        'included_logs': [],
        'excluded': ['images', 'models', 'weights', 'datasets', 'secrets', 'user profile'],
    }
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as package:
        for filename in ALLOWED_LOGS:
            source = logs / filename
            if not source.is_file() or source.is_symlink():
                continue
            with source.open('rb') as handle:
                handle.seek(max(0, source.stat().st_size - MAX_LOG_BYTES))
                raw = handle.read(MAX_LOG_BYTES)
            clean = redact(raw.decode('utf-8', errors='replace'))
            package.writestr('logs/' + filename, clean)
            summary['included_logs'].append(filename)
        package.writestr('diagnostic_summary.json',
                         json.dumps(summary, ensure_ascii=False, indent=2))
        package.writestr('README.txt',
                         'BIMAI360 V271 diagnostic data. Review the ZIP before sharing. '
                         'No model weights, reference images or project files are included.')
    return str(archive)
