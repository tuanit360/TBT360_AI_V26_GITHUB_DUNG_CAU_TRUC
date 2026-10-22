"""V82: one-click import for V81 bundles, ordinary image ZIPs, and wrapper ZIPs.

Never claims that importing pictures has trained model weights.
"""
from __future__ import annotations
import io
import json
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from app.dataset_bundle import import_v81_bundle
from app.dataset_zip_import import import_zip_archive

MANIFEST = 'dataset/USER_DATASET_MANIFEST.json'
IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp')


def inspect_archive(archive):
    with zipfile.ZipFile(archive) as pack:
        names = pack.namelist()
        if MANIFEST in names:
            try:
                data = json.loads(pack.read(MANIFEST))
            except (ValueError, UnicodeError) as exc:
                raise ValueError('Manifest V81 sai định dạng JSON') from exc
            if data.get('schema') != 'tbt360_v81_architecture_raster_sample_v1':
                raise ValueError('Manifest dataset không đúng phiên bản V81')
            return 'v81', None
        images = [name for name in names if name.lower().endswith(IMAGE_EXTENSIONS) and not name.endswith('/')]
        if images:
            return 'images', None
        nested = [
            item for item in pack.infolist()
            if item.filename.lower().endswith('.zip') and not item.is_dir()
        ]
        if len(nested) == 1 and nested[0].file_size <= 250 * 1024 * 1024:
            return 'wrapped', nested[0]
        raise ValueError('Không tìm thấy ảnh hoặc manifest dataset V81 trong ZIP. RAR/SVG/DXF cần xử lý riêng.')


def import_any_zip(root, archive, project_id, caption):
    mode, nested = inspect_archive(archive)
    if mode == 'v81':
        result = import_v81_bundle(root, archive)
    elif mode == 'images':
        result = import_zip_archive(root, archive, project_id, caption)
    else:
        with TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(archive) as pack:
                with pack.open(nested) as input_file:
                    payload = input_file.read(250 * 1024 * 1024 + 1)
                if len(payload) > 250 * 1024 * 1024:
                    raise ValueError('ZIP bên trong quá lớn')
            inner = Path(temp_dir) / 'inner.zip'
            inner.write_bytes(payload)
            inner_mode, more = inspect_archive(inner)
            if inner_mode == 'wrapped':
                raise ValueError('ZIP lồng nhau quá 2 tầng; hãy giải nén một tầng')
            result = import_v81_bundle(root, inner) if inner_mode == 'v81' else import_zip_archive(
                root, inner, project_id, caption
            )
            mode = 'wrapped_' + inner_mode
    result['detected_package'] = mode
    result['training_started'] = False
    return result
