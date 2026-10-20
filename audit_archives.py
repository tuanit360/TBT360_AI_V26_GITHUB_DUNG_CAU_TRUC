"""Safely inventory ZIP archives without extracting potentially unsafe paths."""
import argparse
import collections
import json
import zipfile
from pathlib import Path, PurePosixPath


def audit(path):
    with zipfile.ZipFile(path) as archive:
        counts = collections.Counter()
        unsafe = 0
        total = 0
        for item in archive.infolist():
            if item.is_dir():
                continue
            name = PurePosixPath(item.filename)
            if name.is_absolute() or '..' in name.parts:
                unsafe += 1
                continue
            counts[name.suffix.lower() or '(none)'] += 1
            total += item.file_size
        return {'archive': str(path), 'files': sum(counts.values()), 'uncompressed_bytes': total,
                'unsafe_paths': unsafe, 'extensions': dict(counts.most_common())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('archives', nargs='+', type=Path)
    parser.add_argument('--output', default='dataset_inventory.json')
    args = parser.parse_args()
    result = []
    for path in args.archives:
        try:
            result.append(audit(path))
        except (OSError, zipfile.BadZipFile) as e:
            result.append({'archive': str(path), 'error': str(e)})
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
