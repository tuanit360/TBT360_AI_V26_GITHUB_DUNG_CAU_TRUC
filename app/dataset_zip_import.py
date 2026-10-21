"""Safely list and import PNG/JPG from a user-selected ZIP into the V81 dataset.

Archive entries remain untrusted: no archive paths are extracted to disk,
images are decoded by Pillow, re-encoded to PNG, deduplicated and marked
NEEDS_REVIEW. This does not train a model.
"""
import hashlib
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageOps

SUPPORTED = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
MAX_ENTRIES = 100000
MAX_IMAGES = 500
MAX_IMAGE_BYTES = 25 * 1024 * 1024
MAX_TOTAL_BYTES = 800 * 1024 * 1024


def import_zip_archive(root, archive, project, caption, maximum=MAX_IMAGES):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{2,64}', project or ''):
        raise ValueError('Mã công trình không hợp lệ')
    if not (10 <= len((caption or '').strip()) <= 1500):
        raise ValueError('Mô tả ảnh cần 10–1500 ký tự')
    folder = Path(root).resolve() / 'dataset' / 'raw' / project
    folder.mkdir(parents=True, exist_ok=True)
    manifest = folder / 'import_manifest.jsonl'
    existing = [json.loads(line) for line in manifest.read_text(encoding='utf-8').splitlines() if line.strip()] if manifest.is_file() else []
    hashes = {row.get('sha256_pixels') for row in existing}
    saved, skipped = [], 0
    with zipfile.ZipFile(archive) as pack:
        entries = pack.infolist()
        if len(entries) > MAX_ENTRIES:
            raise ValueError('ZIP chứa quá nhiều file; vui lòng chia thành các gói nhỏ hơn')
        candidates = [entry for entry in entries if not entry.is_dir() and entry.filename.lower().endswith(SUPPORTED)]
        if not candidates:
            raise ValueError('ZIP không chứa ảnh PNG/JPG/WEBP/BMP. Các file SVG/DXF/JSON cần bộ chuyển đổi và nhãn riêng.')
        if sum(entry.file_size for entry in candidates) > MAX_TOTAL_BYTES:
            raise ValueError('Tổng ảnh ZIP vượt 800 MB; chia dữ liệu thành nhiều lượt')
        for entry in candidates[:maximum]:
            if entry.file_size > MAX_IMAGE_BYTES or entry.file_size <= 0:
                skipped += 1
                continue
            try:
                with pack.open(entry) as stream:
                    data = stream.read(MAX_IMAGE_BYTES + 1)
                if len(data) > MAX_IMAGE_BYTES:
                    skipped += 1
                    continue
                with Image.open(io.BytesIO(data)) as source:
                    image = ImageOps.exif_transpose(source).convert('RGB')
                if min(image.size) < 256 or image.width * image.height > 40_000_000:
                    skipped += 1
                    continue
                digest = hashlib.sha256(image.tobytes()).hexdigest()
                if digest in hashes:
                    skipped += 1
                    continue
                file_name = f'{digest[:24]}.png'
                image.save(folder / file_name)
                saved.append({'file_name': file_name, 'source_name': entry.filename[-250:],
                              'project_id': project, 'caption': caption.strip(),
                              'sha256_pixels': digest, 'review_status': 'NEEDS_REVIEW',
                              'imported_utc': datetime.now(timezone.utc).isoformat()})
                hashes.add(digest)
            except (OSError, ValueError, SyntaxError):
                skipped += 1
    if saved:
        with manifest.open('a', encoding='utf-8') as output:
            for item in saved:
                output.write(json.dumps(item, ensure_ascii=False) + '\n')
    return {'imported': len(saved), 'skipped': skipped, 'total_in_project': len(existing) + len(saved),
            'status': 'IMPORTED_AWAITING_REVIEW', 'training_started': False,
            'note': 'Ảnh được kiểm tra, gán nhãn nháp; cần duyệt nhãn/quyền và đánh giá trước huấn luyện.'}
