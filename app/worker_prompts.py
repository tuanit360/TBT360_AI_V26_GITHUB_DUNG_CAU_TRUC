"""Shared prompt text for isolated worker, without importing Gradio."""
DEFAULT = ('professional architectural photography, physically plausible '
           'building geometry, straight vertical walls, consistent floor heights '
           'and window spacing, aligned facade grid, realistic materials and scale, '
           'natural daylight, detailed architecture, crisp but natural architectural visualization')
NEGATIVE = ('watermark, text, captions, logo, oversaturated, low quality, '
            'crooked lines, warped perspective, distorted window grids, '
            'duplicate floors, floating stairs, blurry facade, duplicated buildings, '
            'oversharpening halos')
STYLE = {
    'Kiến trúc chân thực': 'realistic architectural photography, natural daylight, physically plausible materials',
    'Nội thất': 'professional interior photography, cohesive furniture, true-to-life lighting',
    'Ngoại thất chiều tối': 'architectural dusk photography, balanced warm artificial lighting, realistic sky',
    'Phối cảnh xanh': 'biophilic sustainable architecture, mature landscape, realistic vegetation',
    'Tôn trọng hình khối': 'respect the source building proportions, maintain facade organization and camera viewpoint',
}


def build_prompt(brief, style):
    if style not in STYLE:
        raise ValueError('Phong cách không hợp lệ')
    if not isinstance(brief, str) or len(brief) > 2000:
        raise ValueError('Mô tả không hợp lệ')
    return ', '.join(part for part in (DEFAULT, STYLE[style], brief.strip()) if part), NEGATIVE
