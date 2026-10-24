"""V83 architecture composition analysis and conservative crop proposals.

Detects obvious board grids without claiming semantic object recognition.
"""
from pathlib import Path
from PIL import Image, ImageOps, ImageFilter, ImageStat
import json
import hashlib


def propose_crops(image, rows=1, columns=1):
    if not isinstance(image, Image.Image):
        raise ValueError('Cần ảnh PIL hợp lệ')
    rows, columns = int(rows), int(columns)
    if not (1 <= rows <= 8 and 1 <= columns <= 8):
        raise ValueError('Hàng/cột phải từ 1 đến 8')
    source = ImageOps.exif_transpose(image).convert('RGB')
    w, h = source.size
    if min(w // columns, h // rows) < 128:
        raise ValueError('Ô ảnh nhỏ hơn 128 pixel; cần ảnh gốc sắc nét hơn')
    proposals = []
    for row in range(rows):
        for col in range(columns):
            x0 = col * w // columns
            x1 = (col + 1) * w // columns
            y0 = row * h // rows
            y1 = (row + 1) * h // rows
            cropped = source.crop((x0, y0, x1, y1))
            variance = ImageStat.Stat(cropped.convert('L').filter(ImageFilter.FIND_EDGES)).stddev[0]
            proposals.append({
                'row': row + 1, 'column': col + 1, 'bbox_px': [x0, y0, x1, y1],
                'edge_variation': round(float(variance), 3),
                'review_status': 'NEEDS_REVIEW',
                'image': cropped,
            })
    return proposals


def export_crop_review(image, rows, columns, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    proposals = propose_crops(image, rows, columns)
    records = []
    for index, entry in enumerate(proposals, 1):
        path = output_dir / f'crop_{index:03d}.png'
        entry['image'].save(path)
        records.append({key: value for key, value in entry.items() if key != 'image'} |
                       {'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    (output_dir / 'review.json').write_text(json.dumps({
        'schema': 'tbt360.crop_review.v83',
        'mode': 'user_selected_grid_not_automatic_semantics',
        'crops': records,
    }, indent=2), encoding='utf-8')
    return proposals, records
