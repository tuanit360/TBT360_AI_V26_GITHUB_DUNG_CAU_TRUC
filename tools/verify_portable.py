"""Verify every shipped file against the release manifest."""
import hashlib
import json
from pathlib import Path
import sys


def verify(root):
    root = Path(root)
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    failures = []
    failures = []
    for name, record in manifest['files'].items():
        candidate = (root / name).resolve()
        if not candidate.is_relative_to(root.resolve()):
            failures.append(f'Unsafe path: {name}')
            continue
        if not candidate.is_file():
            failures.append(f'Missing: {name}')
            continue
        if candidate.stat().st_size != record['bytes']:
            failures.append(f'Size mismatch: {name}')
            continue
        digest = hashlib.sha256()
        with candidate.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        if digest.hexdigest() != record['sha256']:
            failures.append(f'Hash mismatch: {name}')
    return failures


def verify_release_structure(root):
    """Production-only check, independent from generic checksum verification."""
    root = Path(root)
    failures = []
    required = (
        'BIMAI360.exe',
        'CHAY_BIMAI360_CPU_KHONG_CUDA.bat',
        'MO_LOG_KHONG_CAN_UI.bat',
        'README_PORTABLE.md',
    )
    for filename in required:
        if not (root / filename).is_file():
            failures.append(f'Portable missing required entry point: {filename}')
    allowed_bats = {
        'CHAY_BIMAI360_CPU_KHONG_CUDA.bat',
        'MO_LOG_KHONG_CAN_UI.bat',
    }
    for script in root.glob('*.bat'):
        if script.name not in allowed_bats:
            failures.append(f'Obsolete script shipped: {script.name}')
    if not (root / 'manifest.json').is_file():
        failures.append('Missing manifest.json')
    return failures


if __name__ == '__main__':
    location = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    failures = verify(location) + verify_release_structure(location)
    for entry in failures:
        print('[ERROR]', entry)
    print('PASS' if not failures else 'FAIL')
    sys.exit(0 if not failures else 1)
