"""Audited, project-isolated dataset staging for V72 training.

No model weights are changed by this module. The SHA256 certificate locks the
actual training bytes and validation bytes, not merely a manifest filename.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from learning.data_quality import inspect_training_manifest


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def check_cross_split_pixels(train_folder: Path, validation_folder: Path):
    """Reject identical decoded RGB images even if files are re-encoded."""
    from PIL import Image

    known = set()
    for image_path in sorted(train_folder.glob('*.png')):
        with Image.open(image_path) as image:
            image.load()
            known.add(hashlib.sha256(image.convert('RGB').tobytes()).hexdigest())
    for image_path in sorted(validation_folder.glob('*.png')):
        with Image.open(image_path) as image:
            image.load()
            checksum = hashlib.sha256(image.convert('RGB').tobytes()).hexdigest()
        if checksum in known:
            raise ValueError(
                'Training/validation image pixel leakage: '
                'same image appears in both project splits'
            )


def stage(manifest: Path, root: Path, destination: Path) -> dict:
    from PIL import Image, ImageOps
    manifest, root, destination = manifest.resolve(), root.resolve(), destination.resolve()
    if destination == root or root in destination.parents or destination in root.parents:
        raise ValueError('Training destination must not overlap the source image root')
    if destination.exists():
        raise FileExistsError('Destination already exists. Preserve previous datasets and use a new destination.')
    report = inspect_training_manifest(manifest, root)
    if report['status'] != 'PASS':
        raise ValueError('V71 provenance/project/duplicate audit BLOCKED: ' + '; '.join(report['issues'][:5]))
    lines = [json.loads(line) for line in manifest.read_text(encoding='utf-8').splitlines() if line.strip()]
    by_name = {row['file_name']: row for row in lines}
    if len(by_name) != len(lines):
        raise ValueError('Repeated manifest file_name')
    # Diffusers ImageFolder metadata describes TRAIN only. VAL never enters this folder.
    destination.parent.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix='.v72-staging-', dir=destination.parent))
    try:
        prepared = scratch / 'prepared'
        validation = scratch / 'validation'
        prepared.mkdir()
        validation.mkdir()
        training_rows, validation_rows, artifacts = [], [], []
        for split, names, folder, outputs in (
            ('train', report['train_files'], prepared, training_rows),
            ('validation', report['validation_files'], validation, validation_rows),
        ):
            for index, rel in enumerate(names):
                record = by_name[rel]
                original = (root / rel).resolve()
                if not original.is_relative_to(root) or sha256(original) != record['sha256']:
                    raise ValueError('Source image changed after audit: ' + rel)
                filename = f'{split}_{index:06d}.png'
                with Image.open(original) as img:
                    converted = ImageOps.exif_transpose(img).convert('RGB')
                    converted.save(folder / filename)
                outputs.append({'file_name': filename, 'text': record['caption']})
                artifacts.append({'split': split, 'project_id': record['project_id'],
                                  'filename': filename, 'original_filename': rel,
                                  'source_sha256': record['sha256'],
                                  'staged_sha256': sha256(folder / filename)})
        check_cross_split_pixels(prepared, validation)
        for folder, rows in ((prepared, training_rows), (validation, validation_rows)):
            (folder / 'metadata.jsonl').write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows), encoding='utf-8')
        certificate = {'version': 72, 'status': 'PASS',
                       'source_manifest_sha256': sha256(manifest),
                       'train_projects': report['train_projects'],
                       'validation_projects': report['validation_projects'],
                       'train_count': len(training_rows), 'validation_count': len(validation_rows),
                       'artifacts': artifacts,
                       'warning': 'Provenance permission is self-declared; this audit does not verify correctness of BIM labels or demonstrate GPU training.'}
        certificate['train_metadata_sha256'] = sha256(prepared / 'metadata.jsonl')
        certificate['validation_metadata_sha256'] = sha256(validation / 'metadata.jsonl')
        (scratch / 'certificate.json').write_text(json.dumps(certificate, ensure_ascii=False, indent=2), encoding='utf-8')
        destination.parent.mkdir(parents=True, exist_ok=True)
        scratch.replace(destination)
        return certificate
    finally:
        if scratch.exists():
            shutil.rmtree(scratch)


def verify(destination: Path) -> dict:
    destination = destination.resolve()
    report = json.loads((destination / 'certificate.json').read_text(encoding='utf-8'))
    if report.get('version') != 72 or report.get('status') != 'PASS':
        raise ValueError('Missing approved V72 dataset certificate')
    train_projects = set(report['train_projects'])
    validation_projects = set(report['validation_projects'])
    if not train_projects or not validation_projects or train_projects & validation_projects:
        raise ValueError('Project holdout invalid')
    artifacts = report['artifacts']
    if len(artifacts) != report['train_count'] + report['validation_count']:
        raise ValueError('Record count changed')
    for split in ('train', 'validation'):
        expected = [entry for entry in artifacts if entry['split'] == split]
        folder = destination / ('prepared' if split == 'train' else 'validation')
        manifest = folder / 'metadata.jsonl'
        records = [json.loads(line) for line in manifest.read_text(encoding='utf-8').splitlines() if line.strip()]
        actual_images = {p.name for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}}
        if actual_images != {entry['filename'] for entry in expected}:
            raise ValueError(f'{split} directory contains unapproved or missing images')
        if {r['file_name'] for r in records} != {r['filename'] for r in expected} or len(records) != len(expected):
            raise ValueError(f'{split} metadata differs from approved dataset')
        for entry in expected:
            name = entry['filename']
            if Path(name).name != name or not (folder / name).is_file() or sha256(folder / name) != entry['staged_sha256']:
                raise ValueError(f'{split} image missing or altered: {name}')
            if entry['project_id'] not in (train_projects if split == 'train' else validation_projects):
                raise ValueError('Image assigned to incorrect project split')
            row = next(r for r in records if r['file_name'] == name)
            # Caption tampering must also fail.
            if row.get('text') is None or not isinstance(row['text'], str):
                raise ValueError('Invalid caption')
        # Store/verify a checksum of the metadata in the certificate.
        if report.get(f'{split}_metadata_sha256') != sha256(manifest):
            raise ValueError(f'{split} metadata checksum mismatch')
    check_cross_split_pixels(destination / 'prepared', destination / 'validation')
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    if args.verify:
        outcome = verify(args.output)
    else:
        if args.manifest is None or args.root is None:
            parser.error('--manifest and --root are required to stage data')
        outcome = stage(args.manifest, args.root, args.output)
    print(json.dumps({'status': outcome['status'], 'train_count': outcome['train_count'],
                      'validation_count': outcome['validation_count']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
