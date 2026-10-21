"""Deterministic raster connected-components baseline, NOT a trained AI model.
White foreground on black background; orthogonal filled rectangles only.
User provides calibrated bounds, category and level. Outputs unverified proposals.
"""
from __future__ import annotations
import hashlib
import json
import math
from collections import deque
from pathlib import Path
from PIL import Image


def components(image, threshold=127, min_pixels=4, max_pixels=4_000_000):
    if not (0 <= threshold <= 255 and 1 <= min_pixels <= max_pixels):
        raise ValueError('Invalid recognition parameters')
    if image.mode != 'L':
        image = image.convert('L')
    width, height = image.size
    if width * height > max_pixels or width < 2 or height < 2:
        raise ValueError('Raster too large or too small')
    pix = image.load()
    foreground = bytearray(1 if pix[x, y] > threshold else 0 for y in range(height) for x in range(width))
    visited = bytearray(width * height)
    found = []
    for index, value in enumerate(foreground):
        if not value or visited[index]:
            continue
        queue = deque([index]);visited[index] = 1
        xmin = xmax = index % width; ymin = ymax = index // width
        count = 0
        while queue:
            current = queue.popleft(); x = current % width; y = current // width
            count += 1
            xmin=min(xmin,x);xmax=max(xmax,x);ymin=min(ymin,y);ymax=max(ymax,y)
            for neighbor in (current-width if y else -1, current+width if y+1<height else -1, current-1 if x else -1, current+1 if x+1<width else -1):
                if neighbor>=0 and foreground[neighbor] and not visited[neighbor]:
                    visited[neighbor]=1;queue.append(neighbor)
        if count >= min_pixels:
            box_area=(xmax-xmin+1)*(ymax-ymin+1)
            found.append({'pixel_bbox':[xmin,ymin,xmax+1,ymax+1], 'pixels':count,
                          'rectangularity':round(count/box_area,6)})
    return sorted(found,key=lambda c:(c['pixel_bbox'][1],c['pixel_bbox'][0]))


def propose(image_path, bounds_m, category='wall', level_m=0, threshold=127, min_pixels=4):
    path=Path(image_path)
    if not path.is_file() or path.is_symlink():
        raise ValueError('Image is missing or is a symlink')
    if not isinstance(bounds_m,(tuple,list)) or len(bounds_m)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) for v in bounds_m):
        raise ValueError('Invalid metric bounds')
    left,bottom,right,top=bounds_m
    if right<=left or top<=bottom or category not in ('wall','column','beam','slab'):
        raise ValueError('Unsupported category or extents')
    if type(level_m) not in (int,float) or not math.isfinite(level_m):
        raise ValueError('Invalid level')
    with Image.open(path) as img:
        img.load();width,height=img.size
        parts=components(img, threshold, min_pixels)
    entities=[]
    for i,part in enumerate(parts,1):
        x0,y0,x1,y1=part['pixel_bbox']
        entities.append({'id':f'proposal_{i:04d}', 'type':category, 'level_m':float(level_m),
            'bbox_m':[round(left+x0/width*(right-left),6),round(top-y1/height*(top-bottom),6),
                      round(left+x1/width*(right-left),6),round(top-y0/height*(top-bottom),6)],
            'pixel_bbox':part['pixel_bbox'], 'rectangularity':part['rectangularity'],
            'status':'unverified_raster_proposal'})
    return {'units':'m','verification':'unverified_algorithmic_proposals',
            'source_image_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'bounds_m':list(bounds_m),'image_size':[width,height],
            'limitations':'No learned recognition; labels and scale supplied by user. Connected shapes merge. No doors, host inference or engineering verification.',
            'entities':entities}


def compare(proposals, reference, tolerance_m=0.02):
    if tolerance_m<=0 or not math.isfinite(tolerance_m):
        raise ValueError('Invalid tolerance')
    p=proposals['entities']; r=reference['entities']
    if not r:
        raise ValueError('Reference must contain ground truth')
    if len(p)!=len(r):
        return {'passed':False,'matched':0,'expected':len(r),'predicted':len(p),'maximum_error_m':None}
    used=set(); errors=[]
    for target in r:
        matches=[(max(abs(a-b) for a,b in zip(candidate['bbox_m'],target['bbox_m'])),j)
                 for j,candidate in enumerate(p) if j not in used and candidate['type']==target['type']]
        if not matches:
            return {'passed':False,'matched':len(used),'expected':len(r),'predicted':len(p),'maximum_error_m':None}
        distance,j=min(matches)
        used.add(j);errors.append(distance)
    maximum=max(errors)
    return {'passed':maximum<=tolerance_m,'matched':len(used),'expected':len(r),
            'predicted':len(p),'maximum_error_m':round(maximum,6)}
