"""Optional, real local Hugging Face vision-language inference for architecture.

Never claims a model is installed, fine-tuned on architecture, or geometry
verified unless a real local model completed inference successfully.
"""
import json
import os
from pathlib import Path

from PIL import Image, ImageOps

PROMPT = (
    "Describe visible architectural features only. List roof, facade, openings, "
    "building massing and apparent levels if actually visible. Distinguish "
    "uncertainties clearly. Do not invent room plans, structural dimensions, "
    "MEP layouts or IFC data from a perspective photograph."
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
