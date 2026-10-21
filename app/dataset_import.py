"""One-screen reviewed image import; never starts training automatically."""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageOps

EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
MAX_BYTES = 25 * 1024 * 1024
MAX_FILES = 100


def import_images(root, files, project_id, caption):
    root = Path(root).resolve()
    if not re.fullmatch(r'[A-Za-z0-9_-]{2,64}', (project_id or '').strip()):
        raise ValueError('Mã công trình: 2–64 ký tự chữ, số, _ hoặc -.')
    if not isinstance(caption, str) or not 10 <= len(caption.strip()) <= 1500:
        raise ValueError('Nhập mô tả ảnh dài 10–1500 ký tự.')
    if not files or len(files) > MAX_FILES:
        raise ValueError('Nạp từ 1 đến 100 ảnh trong một lần.')
    target = root / 'dataset' / 'raw' / project_id.strip()
    target.mkdir(parents=True, exist_ok=True)
    metadata_path = target / 'import_manifest.jsonl'
    previous = []
    if metadata_path.exists():
        previous = [json.loads(line) for line in metadata_path.read_text(encoding='utf-8').splitlines() if line.strip()]
    used = {row['sha256_pixels'] for row in previous if row.get('sha256_pixels')}
    imported = []
    skipped = []
    for upload in files:
        # Path objects expose .name (basename only); do not discard parent dirs.
        # Gradio file inputs are string-like paths; file handles expose .name.
        path = Path(upload if isinstance(upload, (str, Path)) else upload.name)
        try:
            if path.suffix.lower() not in EXTENSIONS or not path.is_file() or path.stat().st_size > MAX_BYTES:
                raise ValueError('Chỉ nhận JPEG/PNG/WEBP/BMP tối đa 25 MB.')
            with Image.open(path) as source:
                source.verify()
            with Image.open(path) as source:
                image = ImageOps.exif_transpose(source).convert('RGB')
                if min(image.size) < 256 or image.width * image.height > 40_000_000:
                    raise ValueError('Ảnh cần cạnh ngắn >= 256 px, không vượt 40 megapixel.')
                digest = hashlib.sha256(image.tobytes()).hexdigest()
                if digest in used:
                    skipped.append(f'{path.name}: ảnh trùng')
                    continue
                name = f'{digest[:24]}.png'
                image.save(target / name)
                record = {'file_name': name, 'source_name': path.name,
                          'caption': caption.strip(), 'project_id': project_id.strip(),
                          'sha256_pixels': digest, 'review_status': 'NEEDS_REVIEW',
                          'imported_utc': datetime.now(timezone.utc).isoformat()}
                imported.append(record)
                used.add(digest)
        except (OSError, ValueError, SyntaxError) as exc:
            skipped.append(f'{path.name}: {exc}')
    if imported:
        with metadata_path.open('a', encoding='utf-8') as output:
            for row in imported:
                output.write(json.dumps(row, ensure_ascii=False) + '\n')
    return {
        'imported': len(imported), 'skipped': skipped,
        'total_in_project': len(previous) + len(imported),
        'project_id': project_id.strip(),
        'saved_to': str(target),
        'training_started': False,
        'status': 'IMPORTED_AWAITING_REVIEW',
        'note': 'Đã lưu ảnh và nhãn nháp. Cần duyệt nhãn, quyền sử dụng, chia tập theo công trình và kiểm tra trước khi huấn luyện.',
    }


def preview_project(root, project_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]{2,64}', (project_id or '').strip()):
        return [], {'error': 'Mã công trình không hợp lệ'}
    folder = Path(root).resolve() / 'dataset' / 'raw' / project_id.strip()
    manifest = folder / 'import_manifest.jsonl'
    if not manifest.is_file():
        return [], {'project_id': project_id, 'images': 0, 'message': 'Chưa có ảnh'}
    records = [json.loads(line) for line in manifest.read_text(encoding='utf-8').splitlines() if line.strip()]
    images = [(str(folder / row['file_name']), row['caption']) for row in records[-40:] if (folder / row['file_name']).is_file()]
    return images, {'project_id': project_id, 'images': len(records),
                    'pending_review': sum(row.get('review_status') == 'NEEDS_REVIEW' for row in records),
                    'training_started': False}


def preview_all_projects(root, limit=80):
    """Show installed image examples without asking the user for project IDs."""
    root = Path(root).resolve() / 'dataset' / 'raw'
    if not root.is_dir():
        return [], {'projects': 0, 'images': 0, 'message': 'Chưa có dữ liệu được nạp'}
    gallery = []
    project_counts = {}
    pending = 0
    for folder in sorted(root.iterdir()):
        if not folder.is_dir() or folder.is_symlink() or not re.fullmatch(r'[A-Za-z0-9_-]{2,64}', folder.name):
            continue
        manifest = folder / 'import_manifest.jsonl'
        if not manifest.is_file():
            continue
        try:
            records = [json.loads(line) for line in manifest.read_text(encoding='utf-8').splitlines() if line.strip()]
        except (ValueError, OSError, UnicodeError):
            continue
        project_counts[folder.name] = len(records)
        pending += sum(row.get('review_status') == 'NEEDS_REVIEW' for row in records if isinstance(row, dict))
        for row in records:
            if not isinstance(row, dict):
                continue
            name = row.get('file_name', '')
            if not isinstance(name, str) or Path(name).name != name:
                continue
            image = folder / name
            if image.is_file() and not image.is_symlink():
                gallery.append((str(image), folder.name + ' · ' + str(row.get('caption', ''))[:110]))
    return gallery[:limit], {
        'projects': len(project_counts), 'images': sum(project_counts.values()),
        'pending_review': pending, 'project_counts': project_counts,
        'shown': min(len(gallery), limit), 'training_started': False,
        'note': 'Ảnh đã nạp nhưng nhãn vẫn cần xem xét trước huấn luyện.',
    }
