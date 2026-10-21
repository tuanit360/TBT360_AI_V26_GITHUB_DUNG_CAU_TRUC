"""Read-only SHA256 diagnostic for asset manifests. Never modifies hashes or data."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', default='.')
    p.add_argument('--output', default='sha256_diagnostics.json')
    args = p.parse_args()
    root = Path(args.root).resolve()
    results = []
    seen = set()

    def walk(obj, manifest):
        if isinstance(obj, dict):
            if isinstance(obj.get('path'), str) and isinstance(obj.get('sha256'), str):
                name = obj['path']
                expected = obj['sha256'].lower()
                # Many manifests interpret relative asset paths relative to an assets directory;
                # only report plausible candidates, never silently accept or change them.
                candidates = [manifest.parent / name, root / name, root / 'demo_data' / name]
                for candidate in candidates:
                    resolved = candidate.resolve()
                    if not resolved.is_relative_to(root) or resolved in seen or not resolved.is_file():
                        continue
                    seen.add(resolved)
                    data = resolved.read_bytes()
                    actual = digest(data)
                    lf = digest(data.replace(b'\r\n', b'\n'))
                    crlf = digest(data.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
                    results.append({'manifest': str(manifest.relative_to(root)),
                                    'asset': str(resolved.relative_to(root)),
                                    'expected': expected, 'actual': actual,
                                    'match': expected == actual,
                                    'only_line_ending_difference': expected != actual and expected in (lf, crlf)})
            for value in obj.values():
                walk(value, manifest)
        elif isinstance(obj, list):
            for value in obj:
                walk(value, manifest)

    for manifest in root.rglob('*.json'):
        if any(part in ('.git', '.venv', 'dist', 'build') for part in manifest.parts):
            continue
        try:
            walk(json.loads(manifest.read_text(encoding='utf-8')), manifest)
        except (ValueError, UnicodeError, OSError):
            pass
    output = {'checked_assets': len(results), 'mismatches': sum(not r['match'] for r in results), 'items': results}
    Path(args.output).write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"SHA256 diagnostics: {output['checked_assets']} assets, {output['mismatches']} mismatches")
    for r in results:
        if not r['match']:
            print('MISMATCH', r['asset'], 'line_endings_only=', r['only_line_ending_difference'])


if __name__ == '__main__':
    main()
