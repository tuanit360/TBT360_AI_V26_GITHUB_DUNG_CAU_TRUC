"""Rasterized, explicitly authored, axis-aligned 2D BIM plan evidence. Not an AI predictor."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw

ALLOWED = ('wall', 'door', 'window', 'column', 'beam', 'slab', 'room', 'roof')


def validate_model(model):
    if model.get('units') != 'm':
        raise ValueError('BIM plan requires metric units')
    entities = model.get('entities')
    if not isinstance(entities, list) or not entities:
        raise ValueError('Nonempty BIM entities required')
    by_id = {}
    for item in entities:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id'] or item['id'] in by_id:
            raise ValueError('Missing or duplicate entity id')
        if item.get('type') not in ALLOWED:
            raise ValueError('Unsupported BIM class')
        b = item.get('bbox_m')
        if not isinstance(b, list) or len(b) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) for v in b):
            raise ValueError('Invalid BIM bounding box')
        x0, y0, x1, y1 = b
        if x1 <= x0 or y1 <= y0:
            raise ValueError('Nonpositive BIM dimensions')
        if not isinstance(item.get('level_m'), (int, float)) or not math.isfinite(item['level_m']):
            raise ValueError('Invalid elevation')
        by_id[item['id']] = item
    for item in entities:
        if item['type'] in ('door', 'window'):
            host = by_id.get(item.get('host_id'))
            if host is None or host['type'] != 'wall':
                raise ValueError('Opening must reference a valid host wall')
            a, b = item['bbox_m'], host['bbox_m']
            tolerance = 1e-6
            if a[0] < b[0]-tolerance or a[1] < b[1]-tolerance or a[2] > b[2]+tolerance or a[3] > b[3]+tolerance:
                raise ValueError('Opening bounding box outside host wall')
    return by_id


def render_plan(model, bounds_m, width, height, category):
    validate_model(model)
    if category not in ALLOWED or type(width) is not int or type(height) is not int or not (16 <= width <= 4096 and 16 <= height <= 4096):
        raise ValueError('Invalid raster parameters')
    if not isinstance(bounds_m, list) or len(bounds_m) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) for v in bounds_m):
        raise ValueError('Invalid metric bounds')
    left, bottom, right, top = bounds_m
    if right <= left or top <= bottom:
        raise ValueError('Invalid project extents')
    canvas = Image.new('L', (width, height), 0)
    draw = ImageDraw.Draw(canvas)
    for item in model['entities']:
        if item['type'] != category:
            continue
        x0, y0, x1, y1 = item['bbox_m']
        if min(x1, right) <= max(x0, left) or min(y1, top) <= max(y0, bottom):
            continue
        px0 = max(0, math.floor((x0-left)/(right-left)*width))
        px1 = min(width-1, math.ceil((x1-left)/(right-left)*width)-1)
        py0 = max(0, math.floor((top-y1)/(top-bottom)*height))
        py1 = min(height-1, math.ceil((top-y0)/(top-bottom)*height)-1)
        if px0 <= px1 and py0 <= py1:
            draw.rectangle((px0, py0, px1, py1), fill=255)
    return canvas


def evaluate_plan(model_path, evidence_dir, bounds, width, height, categories, output):
    from evaluation.paired_gate import binary_mask, overlap
    model = json.loads(Path(model_path).read_text(encoding='utf-8'))
    validate_model(model)
    root = Path(evidence_dir).resolve()
    scores = {}
    for category in categories:
        expected = render_plan(model, bounds, width, height, category)
        expected_path = root / (category + '_annotated.png')
        if not expected_path.is_file() or expected_path.is_symlink():
            raise ValueError('Missing independent human-annotated mask: ' + category)
        with Image.open(expected_path) as annot:
            if annot.size != (width, height):
                raise ValueError('Mismatched reference dimensions')
        actual = binary_mask(expected_path)
        computed = (expected.size, [pixel == 255 for pixel in expected.getdata()])
        scores[category] = {'plan_iou': round(overlap(computed, actual), 6)}
    result = {'status':'MEASUREMENT_ONLY', 'metric':'axis-aligned BIM plan bounding-box mask IoU',
              'scores':scores, 'limitations':'Independent annotation required. No 3D/camera projection, AI prediction, engineering certification, or dimensions inferred from imagery.'}
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('model', type=Path)
    p.add_argument('--annotations', type=Path, required=True)
    p.add_argument('--bounds', type=float, nargs=4, required=True, metavar=('LEFT', 'BOTTOM', 'RIGHT', 'TOP'))
    p.add_argument('--width', type=int, required=True)
    p.add_argument('--height', type=int, required=True)
    p.add_argument('--classes', nargs='+', choices=ALLOWED, default=['wall', 'door', 'window'])
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(evaluate_plan(a.model, a.annotations, list(a.bounds), a.width, a.height, a.classes, a.output), indent=2))


if __name__ == '__main__':
    main()
