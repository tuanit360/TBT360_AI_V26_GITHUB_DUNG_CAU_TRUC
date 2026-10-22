"""Optional, real local Hugging Face vision-language inference for architecture.

Never claims a model is installed, fine-tuned on architecture, or geometry
verified unless a real local model completed inference successfully.
"""
import json
import os
from pathlib import Path

from PIL import Image, ImageOps

PROMPT = (
    "Return ONLY valid JSON. Format: "
    '{"observations":{"building_type":{"value":null,"evidence":"","uncertain":true},'
    '"floor_count":{"value":null,"evidence":"","uncertain":true},'
    '"roof_type":{"value":null,"evidence":"","uncertain":true},'
    '"facade_system":{"value":null,"evidence":"","uncertain":true}}}. '
    "Use a positive integer for floor_count and short strings for other values. "
    "Every non-null value must cite a visible feature in evidence. "
    "Use null for unknowns. The uncertain flag must reflect ambiguity. "
    "Do not invent room plans, metric dimensions, MEP, or IFC geometry."
)


def infer_architecture(image, model_path, project_id):
    from app.architecture_observation import inspect_architecture
    observation = inspect_architecture(image, project_id)
    path = Path(model_path).expanduser().resolve()
    if not path.is_dir() or not (path / 'config.json').is_file():
        raise ValueError('Cần thư mục checkpoint VLM local hợp lệ chứa config.json')
    try:
        import torch
        from transformers import AutoProcessor, AutoModelForVision2Seq
    except ImportError as exc:
        raise RuntimeError('Thiếu transformers/torch hỗ trợ Vision2Seq') from exc
    if not torch.cuda.is_available():
        raise RuntimeError('Tính năng VLM yêu cầu CUDA; không tự giả lập suy luận CPU.')
    processor = AutoProcessor.from_pretrained(str(path), local_files_only=True,
                                               trust_remote_code=False)
    model = AutoModelForVision2Seq.from_pretrained(
        str(path), local_files_only=True, trust_remote_code=False,
        torch_dtype=torch.float16).to('cuda').eval()
    rgb = ImageOps.exif_transpose(image).convert('RGB')
    inputs = processor(text=PROMPT, images=rgb, return_tensors='pt')
    inputs = {key: value.to('cuda') for key, value in inputs.items()}
    with torch.inference_mode():
        outputs = model.generate(**inputs, max_new_tokens=256, do_sample=False)
    decoded = processor.batch_decode(outputs, skip_special_tokens=True)[0].strip()
    if not decoded:
        raise RuntimeError('VLM không sinh được kết quả')
    from app.architecture_evidence import parse_vlm_observations
    structured = parse_vlm_observations(decoded)
    observation['structured_observations'] = structured
    observation['vlm'] = {
        'model_directory': path.name,
        'prompt': PROMPT,
        'observations_text': decoded,
        'inference_completed': True,
        'architecture_finetune_verified': False,
        'accuracy_verified': False,
    }
    observation['model_inference_performed'] = True
    observation['recognition_model'] = path.name
    observation['verification_status'] = 'MODEL_OUTPUT_NEEDS_REVIEW'
    return observation
