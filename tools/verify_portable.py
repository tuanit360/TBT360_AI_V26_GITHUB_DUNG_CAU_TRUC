"""Verify every shipped file against the release manifest."""
import hashlib
import json
from pathlib import Path
import sys


def verify(root):
    root = Path(root)
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
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


if __name__ == '__main__':
    location = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    failures = verify(location)
    for entry in failures:
        print('[ERROR]', entry)
    print('PASS' if not failures else 'FAIL')
    sys.exit(0 if not failures else 1)
