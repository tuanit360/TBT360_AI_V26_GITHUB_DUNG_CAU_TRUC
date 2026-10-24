"""Dependency-light Windows preflight; never imports torch or launches Gradio."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import sys
from datetime import datetime, timezone


def probe(root, profile='cpu', port=7861):
    root = Path(root).resolve()
    checks = []
    def record(name, ok, detail, blocking=False):
        checks.append({
            'name': name, 'status': 'PASS' if ok else ('BLOCK' if blocking else 'WARN'),
            'detail': str(detail)
        })
    is_windows = platform.system() == 'Windows'
    record('platform', is_windows, platform.platform(), blocking=False)
    is_64bit = sys.maxsize > 2**32
    record('64bit', is_64bit, platform.machine(), blocking=True)
    record('python', sys.version_info[:2] == (3, 11),
           platform.python_version(), blocking=profile == 'venv')
    target = root / 'logs'
    try:
        target.mkdir(parents=True, exist_ok=True)
        sample = target / ('.probe-' + str(os.getpid()))
        with sample.open('x', encoding='utf-8') as handle:
            handle.write('probe')
        sample.unlink()
        record('filesystem', True, 'Writable logs folder')
    except OSError as exc:
        record('filesystem', False, type(exc).__name__, blocking=True)
    free = shutil.disk_usage(root if root.exists() else Path.cwd()).free
    record('disk_space', free >= 1024**3, f'{free // (1024**2)} MiB free')
    if profile == 'venv':
        for package in ('gradio', 'Pillow', 'torch', 'diffusers', 'transformers'):
            try:
                version = importlib.metadata.version(package)
                record('dependency_' + package, True, version)
            except importlib.metadata.PackageNotFoundError:
                record('dependency_' + package, False, 'Not installed', blocking=True)
    if profile == 'cuda':
        tool = shutil.which('nvidia-smi')
        record('nvidia_smi', bool(tool), tool or 'NVIDIA driver tool absent',
               blocking=True)
    try:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', port))
        record('port', True, f'127.0.0.1:{port} available')
    except OSError as exc:
        record('port', False, f'{port}: {type(exc).__name__}', blocking=True)
    result = {
        'schema': 'bimai360.preflight.v274',
        'utc': datetime.now(timezone.utc).isoformat(),
        'profile': profile,
        'checks': checks,
        'ready': not any(item['status'] == 'BLOCK' for item in checks),
        'warning_count': sum(item['status'] == 'WARN' for item in checks),
    }
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--profile', choices=['cpu', 'venv', 'cuda'], default='cpu')
    parser.add_argument('--port', type=int, default=7861)
    parser.add_argument('--output')
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error('--port must be 1..65535')
    report = probe(args.root, args.profile, args.port)
    serialized = json.dumps(report, indent=2, ensure_ascii=False)
    print(serialized)
    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + '.tmp')
        temporary.write_text(serialized, encoding='utf-8')
        os.replace(temporary, destination)
    return 0 if report['ready'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
