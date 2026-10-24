"""Inventory user-provided architecture archives without asserting BIM ground truth.

Supports directories, ZIP, and RAR when an actual RAR backend is installed.
Names and images alone never imply engineering/IFC verification.
"""
import argparse
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path

IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp', '.tiff', '.tif'}
DRAWING_SUFFIXES = {'.dxf', '.dwg', '.svg', '.pdf'}
BIM_SUFFIXES = {'.ifc', '.glb', '.gltf', '.rvt', '.skp'}
MAX_MEMBERS = 50000


def _classification(name):
    extension = Path(name).suffix.lower()
    if extension in IMAGE_SUFFIXES:
        return 'image_unlabeled'
    if extension in DRAWING_SUFFIXES:
        return 'drawing_unverified'
    if extension in BIM_SUFFIXES:
        return 'model_unverified'
    if extension in {'.json', '.jsonl', '.csv', '.txt'}:
        return 'potential_metadata'
    return 'other'


def audit_archives(paths):
    entries = []
    failures = []
    for archive_path in paths:
        path = Path(archive_path)
        if not path.is_file():
            failures.append({'source': path.name, 'error': 'file_missing'})
            continue
        try:
            if path.suffix.lower() == '.zip':
                with zipfile.ZipFile(path) as archive:
                    names = [m.filename for m in archive.infolist() if not m.is_dir()]
            elif path.suffix.lower() == '.rar':
                try:
                    import rarfile
                except ImportError as exc:
                    raise RuntimeError('Install rarfile and a compatible RAR backend') from exc
                with rarfile.RarFile(path) as archive:
                    names = [m.filename for m in archive.infolist() if not m.isdir()]
            else:
                raise ValueError('Only ZIP/RAR archives accepted')
            if len(names) > MAX_MEMBERS:
                raise ValueError('Archive exceeds 50000 files')
            normalized = set()
            for name in names:
                pure = name.replace('\\', '/')
                if pure.startswith('/') or '..' in pure.split('/') or not pure:
                    raise ValueError('Archive contains unsafe path')
                normalized.add(pure.casefold())
                entries.append({'archive': path.name, 'relative_path': pure,
                                'category': _classification(pure),
                                'label_verified': False,
                                'geometry_verified': False})
            if len(normalized) != len(names):
                failures.append({'source': path.name, 'error': 'duplicate_archive_paths'})
        except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
            failures.append({'source': path.name, 'error': str(exc)[:200]})
    totals = Counter(item['category'] for item in entries)
    return {'schema': 'bimai360.user_dataset_audit.v211',
            'archive_count': len(paths), 'files': entries,
            'totals': dict(sorted(totals.items())),
            'uninspected_archives': failures,
            'training_ready': False,
            'training_ready_reason': 'Needs project IDs, matched image/drawing/BIM labels, rights and holdout split'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('archives', nargs='+')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = audit_archives(args.archives)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Discovered', len(result['files']), 'archive entries; errors', len(result['uninspected_archives']))
    if result['uninspected_archives']:
        raise SystemExit(2)
