"""V83 conservative concept-to-BIM handoff.

Exports raster and SVG references plus explicit conceptual metadata. It does
NOT create IFC/RVT/SKP or assert dimensions inferred from photographs.
"""
import hashlib
import json
from pathlib import Path
from xml.sax.saxutils import escape
from PIL import Image, ImageOps


def build_prompt(building_type, floors, facade, roof, camera, lighting, materials):
    if not 1 <= int(floors) <= 100:
        raise ValueError('Số tầng phải từ 1 đến 100')
    values = [building_type, facade, roof, camera, lighting, materials]
    if any(not isinstance(value, str) or len(value) > 120 for value in values):
        raise ValueError('Thuộc tính mô tả không hợp lệ')
    return ', '.join([
        f'{int(floors)}-story {building_type.strip()}',
        facade.strip(), roof.strip(), materials.strip(), camera.strip(),
        lighting.strip(), 'consistent facade rhythm, realistic proportions, architectural photography',
    ])


def export_handoff(image, output_folder, *, prompt, seed, project_id, floors_hint=None):
    if not isinstance(image, Image.Image):
        raise ValueError('Cần ảnh kết quả')
    if not isinstance(project_id, str) or not project_id.replace('_', '').replace('-', '').isalnum():
        raise ValueError('Mã công trình không hợp lệ')
    if len(project_id) > 64 or not project_id:
        raise ValueError('Mã công trình không hợp lệ')
    if len(prompt) > 2000 or not prompt.strip():
        raise ValueError('Prompt không hợp lệ')
    target = Path(output_folder)
    target.mkdir(parents=True, exist_ok=True)
    source = ImageOps.exif_transpose(image).convert('RGB')
    raster = target / 'concept_reference.png'
    source.save(raster)
    w, h = source.size
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" '
           f'viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
           f'<title>{escape(project_id)} – concept raster reference</title>'
           '<desc>Image reference only: no vector geometry, CAD dimensions or BIM elements.</desc>'
           '</svg>')
    (target / 'reference_canvas.svg').write_text(svg, encoding='utf-8')
    data = {
        'schema': 'tbt360.ai_to_bim_handoff.v83',
        'project_id': project_id,
        'reference_image': raster.name,
        'reference_image_sha256': hashlib.sha256(raster.read_bytes()).hexdigest(),
        'seed': int(seed),
        'prompt': prompt,
        'image_size_px': [w, h],
        'estimated_floor_count_user_hint': floors_hint,
        'units': 'pixels_only_no_real_world_scale',
        'model_status': 'concept_not_BIM',
        'geometry_validated': False,
        'engineering_verified': False,
        'needs_user_measurements': True,
        'next_step': 'Trace and scale in CAD/BIM modeler; confirm elements, levels and dimensions before exporting IFC.',
    }
    (target / 'handoff.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    from app.canonical_bim_contract import build_handoff, save_handoff
    save_handoff(target, build_handoff(project_id, units='m', level_ids=[], elements=[]))
    return data
