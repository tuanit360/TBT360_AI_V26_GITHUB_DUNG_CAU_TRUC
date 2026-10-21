"""Install reviewed-for-import V81 *draft* image bundles into dataset/raw.

Bundle images and manifest metadata are untrusted. Never extract arbitrary
archive members; validate every image's pixel hash before writing any file.
This is DATA IMPORT only, not model training or label verification.
"""
from __future__ import annotations
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from PIL import Image, ImageOps

SCHEMA = 'tbt360_v81_architecture_raster_sample_v1'
PROJECT = re.compile(r'^[A-Za-z0-9_-]{2,64}$')
IMAGE_NAME = re.compile(r'^[0-9a-f]{24}\\.(jpg|jpeg|png)$')
MAX_ITEMS = 1000
MAX_BYTES = 200 * 1024 * 1024


def import_v81_bundle(root, archive):
    destination = Path(root).resolve() / 'dataset' / 'raw'
    planned = []
    total = 0
    with zipfile.ZipFile(archive) as z:
        try:
            metadata = json.loads(z.read('dataset/USER_DATASET_MANIFEST.json'))
        except (KeyError, ValueError) as exc:
            raise ValueError('Không phải gói dataset V81 có manifest hợp lệ') from exc
        if metadata.get('schema') != SCHEMA:
            raise ValueError('Sai phiên bản manifest dataset V81')
        projects = metadata.get('project_summary')
        if not isinstance(projects, list) or not projects:
            raise ValueError('Gói chưa có thông tin nhóm ảnh')
        seen = set()
        for entry in projects:
            project_id = entry.get('project_id') if isinstance(entry, dict) else None
            if not isinstance(project_id, str) or not PROJECT.fullmatch(project_id) or project_id in seen:
                raise ValueError('Mã nhóm ảnh không hợp lệ hoặc trùng')
            seen.add(project_id)
            file_key = f'dataset/raw/{project_id}/import_manifest.jsonl'
            try:
                lines = z.read(file_key).decode('utf-8').splitlines()
            except (KeyError, UnicodeDecodeError) as exc:
                raise ValueError('Thiếu danh sách nhãn ảnh cho nhóm ' + project_id) from exc
            if len(lines) != entry.get('imported_images'):
                raise ValueError('Số lượng ảnh và nhãn không khớp')
            for line in lines:
                if len(planned) >= MAX_ITEMS:
                    raise ValueError('Vượt giới hạn 1.000 ảnh cho một lượt nạp')
                try:
                    record = json.loads(line)
                except ValueError as exc:
                    raise ValueError('Nhãn ảnh không phải JSON hợp lệ') from exc
                file_name = record.get('file_name', '')
                if not isinstance(file_name, str) or not IMAGE_NAME.fullmatch(file_name):
                    raise ValueError('Tên file ảnh không an toàn')
                if record.get('project_id') != project_id or record.get('review_status') != 'NEEDS_REVIEW':
                    raise ValueError('Nhãn hoặc trạng thái kiểm tra không hợp lệ')
                file_path = f'dataset/raw/{project_id}/{file_name}'
                try:
                    member = z.getinfo(file_path)
                    if member.file_size > 25 * 1024 * 1024:
                        raise ValueError('Ảnh vượt giới hạn dung lượng')
                    total += member.file_size
                    if total > MAX_BYTES:
                        raise ValueError('Tổng dữ liệu vượt 200 MB')
                    data = z.read(member)
                    with Image.open(io.BytesIO(data)) as image:
                        image = ImageOps.exif_transpose(image).convert('RGB')
                        if min(image.size) < 256 or image.width * image.height > 10_000_000:
                            raise ValueError('Kích thước ảnh không hợp lệ')
                        actual_hash = hashlib.sha256(image.tobytes()).hexdigest()
                    if actual_hash != record.get('sha256_pixels'):
                        raise ValueError('SHA256 pixel ảnh không khớp')
                    planned.append((project_id, file_name, data, record))
                except KeyError as exc:
                    raise ValueError('Thiếu ảnh trong gói dữ liệu: ' + file_name) from exc
    imported, duplicates = 0, 0
    counts = {}
    for project_id, file_name, data, record in planned:
        folder = destination / project_id
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / file_name
        manifest_path = folder / 'import_manifest.jsonl'
        if target.exists():
            if target.read_bytes() != data:
                raise ValueError('File trùng tên nhưng nội dung khác: ' + file_name)
            duplicates += 1
            continue
        target.write_bytes(data)
        with manifest_path.open('a', encoding='utf-8') as output:
            output.write(json.dumps(record, ensure_ascii=False) + '\n')
        imported += 1
        counts[project_id] = counts.get(project_id, 0) + 1
    return {
        'status': 'IMPORTED_AWAITING_REVIEW',
        'new_images': imported,
        'already_imported': duplicates,
        'projects': sorted(seen),
        'new_images_by_project': counts,
        'training_started': False,
        'message': 'Đã nạp ảnh có nhãn nháp theo nhóm; cần duyệt trước khi học.',
    }
