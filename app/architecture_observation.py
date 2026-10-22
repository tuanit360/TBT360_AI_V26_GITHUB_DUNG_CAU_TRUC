"""V112–V116 architecture visual observations for subsequent AI/BIM workflows.

Observed pixel geometry is not building geometry. Explicit unknown values
prevent an untrained heuristic from fabricating floors, depths or dimensions.
"""
from PIL import Image, ImageOps, ImageFilter, ImageStat
import hashlib
import json


def inspect_architecture(image, project_id, image_role='exterior_perspective'):
    if not isinstance(image, Image.Image):
        raise ValueError('Ảnh không hợp lệ')
    if image_role not in ('exterior_perspective', 'interior', 'floorplan', 'elevation', 'section'):
        raise ValueError('Loại ảnh không hỗ trợ')
    if not isinstance(project_id, str) or not project_id.replace('_', '').replace('-', '').isalnum() or len(project_id) > 64 or not project_id:
        raise ValueError('Mã công trình không hợp lệ')
    image = ImageOps.exif_transpose(image).convert('RGB')
    if min(image.size) < 256 or image.width * image.height > 40_000_000:
        raise ValueError('Ảnh phải lớn hơn 256px và nhỏ hơn 40MP')
    pixels = image.tobytes()
    edges = image.convert('L').filter(ImageFilter.FIND_EDGES)
    edge_density = round(ImageStat.Stat(edges).mean[0], 3)
    return {
        'schema': 'bimai360.architecture_observation.v116',
        'project_id': project_id,
        'source_role': image_role,
        'image_size_px': list(image.size),
        'image_pixels_sha256': hashlib.sha256(pixels).hexdigest(),
        'observed_image_features': {'edge_strength_mean': edge_density},
        'architecture_hypotheses': {
            'building_type': None, 'floor_count': None,
            'roof_type': None, 'facade_system': None,
            'camera_pose': None, 'metric_scale': None,
        },
        'bim_entities': [],
        'recognition_model': None,
        'model_inference_performed': False,
        'verification_status': 'NEEDS_REVIEW',
        'guidance': 'Enter verified dimensions and review hypotheses before BIM synthesis.',
    }


def combine_project_observations(observations):
    if not isinstance(observations, list) or not observations:
        raise ValueError('Cần ít nhất một ảnh đã phân tích')
    project = observations[0].get('project_id')
    seen = set()
    entries = []
    for item in observations:
        if item.get('schema') != 'bimai360.architecture_observation.v116' or item.get('project_id') != project:
            raise ValueError('Không thể trộn ảnh từ các công trình hoặc schema khác nhau')
        digest = item.get('image_pixels_sha256')
        if digest in seen:
            continue
        seen.add(digest)
        entries.append(item)
    return {
        'schema': 'bimai360.project_observations.v116', 'project_id': project,
        'views': entries, 'view_count': len(entries),
        'cross_view_geometry_verified': False,
        'requires_user_design_constraints': True,
        'bim_export_ready': False,
    }
