"""Local workspace preferences and append-only operational diagnostics.

This is NOT remote authentication. Do not embed, persist or log passwords.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import logging
import re

LOGGER_NAME = 'bimai360.operation'


def _workspace_root(root):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def setup_runtime_log(root):
    home = _workspace_root(root)
    log_dir = home / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    log_file = (log_dir / 'bimai360_operations.log').resolve()
    if not any(
        isinstance(handler, logging.FileHandler)
        and Path(handler.baseFilename).resolve() == log_file
        for handler in logger.handlers
    ):
        handler = logging.FileHandler(log_file, encoding='utf-8')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s'
        ))
        logger.addHandler(handler)
    logger.propagate = False
    return logger


def record_operation(root, action, status='started'):
    if action not in {
        'workspace_open', 'generate', 'dataset_import', 'concept_export',
        'check_model', 'export_file', 'vlm_inference', 'training_preflight'
    }:
        raise ValueError('Unsupported operation name')
    if status not in {'started', 'completed', 'failed'}:
        raise ValueError('Unsupported operation status')
    setup_runtime_log(root).info('%s | %s', action, status)


def save_local_profile(root, name):
    if not isinstance(name, str) or not re.fullmatch(
        r'[\w\s.-]{1,64}', name, flags=re.UNICODE
    ):
        raise ValueError('Tên hiển thị không hợp lệ')
    home = _workspace_root(root)
    destination = home / 'local_workspace.json'
    profile = {
        'mode': 'offline_local',
        'display_name': name.strip(),
        'last_opened_utc': datetime.now(timezone.utc).isoformat(),
        'server_authenticated': False,
        'credentials_stored': False
    }
    destination.write_text(json.dumps(
        profile, ensure_ascii=False, indent=2
    ), encoding='utf-8')
    record_operation(root, 'workspace_open', 'completed')
    return profile


def read_runtime_log(root, lines=100):
    file = _workspace_root(root) / 'logs' / 'bimai360_operations.log'
    if not file.is_file():
        return 'Chưa có nhật ký hoạt động.'
    with file.open('r', encoding='utf-8', errors='replace') as stream:
        return ''.join(stream.readlines()[-min(max(int(lines), 1), 200):])
