"""Optional advanced image pipelines. All heavyweight imports are lazy.
No downloaded weights are distributed in the source ZIP.
"""
from __future__ import annotations
import hashlib
import json
import os
import time
from pathlib import Path
from PIL import Image, ImageFilter, ImageOps

ROOT = Path(os.environ.get('TBT360_HOME', Path(__file__).resolve().parents[1]))
CACHE = ROOT / 'models'
MODEL_IDS = {
    'SD 1.5': 'stable-diffusion-v1-5/stable-diffusion-v1-5',
    'SDXL 1.0': 'stabilityai/stable-diffusion-xl-base-1.0',
}
CONTROL_IDS = {
    'SD 1.5': 'lllyasviel/control_v11p_sd15_canny',
    'SDXL 1.0': 'diffusers/controlnet-canny-sdxl-1.0',
}
UPSCALE_ID = 'stabilityai/stable-diffusion-x4-upscaler'


def local_or_hub(repo: str, folder: str) -> str:
    local = CACHE / folder
    return str(local) if (local / 'model_index.json').is_file() else repo


def validate_advanced(model: str, strength: float, steps: int, guidance: float, control_scale: float):
    if model not in MODEL_IDS:
        raise ValueError('Model không hợp lệ')
    if not (0.1 <= float(strength) <= 0.9):
        raise ValueError('Strength phải thuộc [0.1, 0.9]')
    if not (10 <= int(steps) <= 60):
        raise ValueError('Steps phải thuộc [10, 60]')
    if not (1 <= float(guidance) <= 15):
        raise ValueError('CFG phải thuộc [1, 15]')
    if not (0 <= float(control_scale) <= 2):
        raise ValueError('Control strength phải thuộc [0, 2]')


def make_canny(image: Image.Image, width: int, height: int) -> Image.Image:
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError('Cần cài opencv-python-headless để dùng ControlNet Canny') from exc
    target = ImageOps.fit(ImageOps.exif_transpose(image).convert('RGB'), (width, height))
    edges = cv2.Canny(np.asarray(target), 100, 200)
    return Image.fromarray(edges).convert('RGB')


def choose_size(model: str, image: Image.Image) -> tuple[int, int]:
    max_dim = 1024 if model == 'SDXL 1.0' else 640
    width, height = image.size
    ratio = min(max_dim / max(width, height), 1.0)
    return (max(64, int(width * ratio) // 64 * 64), max(64, int(height * ratio) // 64 * 64))


def generate_advanced(image: Image.Image, prompt: str, model: str, control: bool,
                      strength: float, steps: int, guidance: float,
                      control_scale: float, seed: int, low_vram: bool,
                      callback=None):
    if image is None or not isinstance(image, Image.Image):
        raise ValueError('Cần ảnh nguồn')
    if len(prompt or '') > 2000 or not (prompt or '').strip():
        raise ValueError('Prompt không hợp lệ')
    validate_advanced(model, strength, steps, guidance, control_scale)
    import torch
    from diffusers import AutoPipelineForImage2Image
    if not torch.cuda.is_available():
        raise RuntimeError('SDXL/ControlNet yêu cầu CUDA trong workflow này; dùng tab V67 cho CPU')
    dtype = torch.float16
    offline = os.environ.get('TBT360_OFFLINE') == '1'
    width, height = choose_size(model, image)
    prepared = ImageOps.fit(image.convert('RGB'), (width, height))
    kwargs = {'torch_dtype': dtype, 'use_safetensors': True, 'cache_dir': str(CACHE), 'local_files_only': offline}
    control_image = None
    pipe = None
    try:
        if control:
            from diffusers import ControlNetModel, StableDiffusionControlNetImg2ImgPipeline, StableDiffusionXLControlNetImg2ImgPipeline
            cname = 'control_sdxl' if model == 'SDXL 1.0' else 'control_sd15'
            network = ControlNetModel.from_pretrained(local_or_hub(CONTROL_IDS[model], cname), **kwargs)
            cls = StableDiffusionXLControlNetImg2ImgPipeline if model == 'SDXL 1.0' else StableDiffusionControlNetImg2ImgPipeline
            pipe = cls.from_pretrained(local_or_hub(MODEL_IDS[model], 'sdxl' if model == 'SDXL 1.0' else 'sd15'), controlnet=network, **kwargs)
            control_image = make_canny(prepared, width, height)
        else:
            pipe = AutoPipelineForImage2Image.from_pretrained(local_or_hub(MODEL_IDS[model], 'sdxl' if model == 'SDXL 1.0' else 'sd15'), **kwargs)
        if low_vram:
            pipe.enable_model_cpu_offload()
        else:
            pipe.to('cuda')
        pipe.enable_vae_slicing()
        if hasattr(pipe, 'enable_vae_tiling'):
            pipe.enable_vae_tiling()
        generator = torch.Generator(device='cpu').manual_seed(int(seed))
        args = dict(prompt=prompt, image=prepared, strength=float(strength),
                    num_inference_steps=int(steps), guidance_scale=float(guidance), generator=generator)
        if control:
            args.update(control_image=control_image, controlnet_conditioning_scale=float(control_scale))
        result = pipe(**args).images[0]
        if callback:
            callback(result)
        return result, {'model': MODEL_IDS[model], 'controlnet': CONTROL_IDS[model] if control else None,
                        'seed': int(seed), 'resolution': list(result.size), 'steps': int(steps),
                        'strength': float(strength), 'guidance': float(guidance),
                        'control_scale': float(control_scale) if control else None,
                        'status': 'INFERENCE_COMPLETED_CONCEPT_NOT_BIM'}
    finally:
        del pipe
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def upscale_ai(image: Image.Image, prompt: str, seed: int, low_vram: bool):
    if image is None:
        raise ValueError('Cần ảnh nguồn')
    import torch
    from diffusers import StableDiffusionUpscalePipeline
    if not torch.cuda.is_available():
        raise RuntimeError('AI x4 upscale chỉ kích hoạt khi có CUDA')
    # Upscaler accepts a low-resolution image; bounded for memory safety.
    source = ImageOps.contain(image.convert('RGB'), (384, 384))
    if min(source.size) < 64:
        raise ValueError('Ảnh nguồn quá nhỏ')
    pipe = None
    try:
        pipe = StableDiffusionUpscalePipeline.from_pretrained(
            local_or_hub(UPSCALE_ID, 'x4_upscaler'), torch_dtype=torch.float16,
            use_safetensors=True, cache_dir=str(CACHE),
            local_files_only=os.environ.get('TBT360_OFFLINE') == '1')
        if low_vram:
            pipe.enable_model_cpu_offload()
        else:
            pipe.to('cuda')
        result = pipe(prompt=prompt or 'high quality architectural photography', image=source,
                      generator=torch.Generator(device='cpu').manual_seed(int(seed)),
                      num_inference_steps=25).images[0]
        return result, {'pipeline': UPSCALE_ID, 'method':'DIFFUSION_AI_UPSCALE',
                        'seed':int(seed), 'input_resolution':list(source.size),
                        'output_resolution':list(result.size),
                        'warning':'AI upscale có thể thay đổi chi tiết kiến trúc; không dùng làm tài liệu BIM'}
    finally:
        del pipe
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
