"""Crash-safe ZIP publication for generated image batches."""
import hashlib
import os
from pathlib import Path
import tempfile
import zipfile


def publish_directory_zip(source_dir, destination):
    """Publish only a complete verified archive; preserve previous on errors."""
    source_dir = Path(source_dir)
    destination = Path(destination)
    files = sorted(path for path in source_dir.iterdir() if path.is_file())
    if not files:
        raise ValueError('No export files')
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=destination.name + '.', suffix='.part',
            dir=destination.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
        digests = {}
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                digests[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
                archive.write(path, arcname=path.name)
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() is not None or set(archive.namelist()) != set(digests):
                raise IOError('ZIP integrity check failed')
            for name, digest in digests.items():
                if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                    raise IOError('ZIP content checksum mismatch')
        with temporary.open('r+b') as handle:
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        return destination
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
