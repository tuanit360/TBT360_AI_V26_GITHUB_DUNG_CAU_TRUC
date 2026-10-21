"""Deterministic diagnostic metrics: NOT an aesthetic/engineering score."""
from __future__ import annotations
import hashlib
import math
from PIL import Image, ImageFilter, ImageOps, ImageStat


def image_diagnostics(image: Image.Image) -> dict:
    if not isinstance(image, Image.Image):
        raise TypeError('Expected PIL image')
    normalized = ImageOps.exif_transpose(image).convert('RGB')
    gray = normalized.convert('L')
    # Resize for bounded diagnostic processing independently of output size.
    gray.thumbnail((640, 640), Image.Resampling.LANCZOS)
    stats = ImageStat.Stat(gray)
    edges = gray.filter(ImageFilter.FIND_EDGES)
    edge_stats = ImageStat.Stat(edges)
    histogram = gray.histogram()
    count = max(1, sum(histogram))
    dark_fraction = sum(histogram[:12]) / count
    bright_fraction = sum(histogram[244:]) / count
    return {
        'width': normalized.width,
        'height': normalized.height,
        'mean_luminance_0_255': round(stats.mean[0], 2),
        'luminance_stddev': round(stats.stddev[0], 2),
        'edge_energy_proxy': round(edge_stats.mean[0], 2),
        'near_black_fraction': round(dark_fraction, 4),
        'near_white_fraction': round(bright_fraction, 4),
        'pixel_sha256': hashlib.sha256(normalized.tobytes()).hexdigest(),
        'method': 'downsampled grayscale / PIL edge proxy; not perceptual IQA',
    }


def diagnostic_notes(diag: dict) -> list[str]:
    warnings = []
    if diag['near_black_fraction'] > 0.20:
        warnings.append('Large near-black region; inspect exposure and intended night scene')
    if diag['near_white_fraction'] > 0.20:
        warnings.append('Large near-white region; inspect clipping and reference background')
    if diag['luminance_stddev'] < 20:
        warnings.append('Low grayscale contrast; inspect visually')
    if min(diag['width'], diag['height']) < 512:
        warnings.append('Native resolution is low; resizing will not add real detail')
    return warnings
