"""Publish exactly verified outputs and verify the child-worker receipt."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

from PIL import Image
import shutil


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for piece in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(piece)
    return digest.hexdigest()


def streams_match(left, right):
    while True:
        first = left.read(1024 * 1024)
        second = right.read(1024 * 1024)
        if first != second:
            return False
        if not first:
            return True



def atomic_json(destination, data):
    destination = Path(destination)
    with tempfile.NamedTemporaryFile(
        mode='w', encoding='utf-8', dir=destination.parent,
        prefix=destination.name + '.', suffix='.part', delete=False,
    ) as handle:
        temporary = Path(handle.name)
        try:
            json.dump(data, handle, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    os.replace(temporary, destination)


def publish_selected_outputs(folder, archive_path, names):
    folder = Path(folder).resolve()
    archive_path = Path(archive_path).resolve()
    if archive_path.parent != folder.parent:
        raise ValueError('ZIP must be sibling of isolated job directory')
    names = list(names)
    if len(names) > 6 or not names or len(names) != len(set(names)):
        raise ValueError('Duplicate or empty output manifest')
    for name in names:
        if not isinstance(name, str) or Path(name).name != name:
            raise ValueError('Unsafe output filename')
        item = folder / name
        if item.is_symlink() or not item.is_file() or item.stat().st_size == 0:
            raise ValueError('Missing or empty output')
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=archive_path.name + '.', suffix='.part',
        dir=archive_path.parent, delete=False,
    ) as handle:
        temporary = Path(handle.name)
    try:
        digests = {}
        with ZipFile(temporary, 'w', ZIP_DEFLATED) as archive:
            for name in names:
                digests[name] = sha256_file(folder / name)
                archive.write(folder / name, arcname=name)
        with ZipFile(temporary) as archive:
            if archive.testzip() is not None or set(archive.namelist()) != set(names):
                raise ValueError('Invalid ZIP structure')
            for name, digest in digests.items():
                output_hash = hashlib.sha256()
                with archive.open(name) as member:
                    for piece in iter(lambda: member.read(1024 * 1024), b''):
                        output_hash.update(piece)
                if output_hash.hexdigest() != digest:
                    raise ValueError('Output checksum mismatch')
        os.replace(temporary, archive_path)
    finally:
        temporary.unlink(missing_ok=True)
    return archive_path


def verify_worker_receipt(report, folder):
    folder = Path(folder).resolve()
    archive = folder.with_suffix('.zip')
    if report.get('status') != 'PASS_REAL_INFERENCE':
        raise ValueError('Unsuccessful worker receipt')
    if Path(str(report.get('archive', ''))).resolve() != archive:
        raise ValueError('Wrong worker archive')
    if not archive.is_file():
        raise ValueError('Worker ZIP missing')
    if sha256_file(archive) != report.get('sha256'):
        raise ValueError('Worker ZIP hash mismatch')
    images = report.get('images')
    if not isinstance(images, list) or not 1 <= len(images) <= 4:
        raise ValueError('Invalid worker image list')
    with ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise ValueError('ZIP CRC invalid')
        names = bundle.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate ZIP members')
        if any(name in names for name in ('job.json', 'reference_input.png')):
            raise ValueError('Private inputs leaked in ZIP')
        png_members = [name for name in names if name.lower().endswith('.png')]
        if len(png_members) != len(images):
            raise ValueError('Unexpected PNG in ZIP archive')
        expected = {'generation.json'}
        for item in images:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                raise ValueError('Invalid image tuple')
            expected.add(Path(str(item[0])).name)
        if set(names) != expected:
            raise ValueError('ZIP manifest contains unexpected files')
        for item in images:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                raise ValueError('Invalid image tuple')
            path = Path(str(item[0])).resolve()
            if path.parent != folder or path.suffix.lower() != '.png':
                raise ValueError('Unexpected output image location')
            if not path.is_file() or path.name not in names:
                raise ValueError('Output image missing')
            with Image.open(path) as image:
                image.verify()
            with path.open('rb') as source, bundle.open(path.name) as packaged:
                if not streams_match(source, packaged):
                    raise ValueError('PNG and ZIP mismatch')
    return True
