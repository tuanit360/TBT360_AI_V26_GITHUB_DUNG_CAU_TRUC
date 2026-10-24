"""Run actual SD1.5 image-to-image inference; never claim PASS without PNG.

Requires a locally installed, licensed Diffusers SD1.5 checkpoint. Not part
of the CPU-only CI smoke, which lacks model weights.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def run(model_dir, output_dir, device='auto'):
    from PIL import Image
    import torch
    from diffusers import AutoPipelineForImage2Image

    model_dir = Path(model_dir).resolve()
    output_dir = Path(output_dir).resolve()
    if not (model_dir / 'model_index.json').is_file():
        raise RuntimeError('Thiếu checkpoint SD1.5 Diffusers: model_index.json')
    from app.cpu_readiness import inspect_local_assets
    # Require complete model components before loading costly weights.
    if model_dir.name == 'sd15' and model_dir.parent.name == 'models':
        status = inspect_local_assets(model_dir.parent.parent)
        if not status['model_files_complete']:
            raise RuntimeError('Checkpoint chưa đủ: ' + ', '.join(status['missing_components']))
    output_dir.mkdir(parents=True, exist_ok=True)
    if device not in ('auto', 'cpu', 'cuda'):
        raise ValueError('Unsupported device')
    cuda = bool(getattr(getattr(torch, 'version', None), 'cuda', None)) and torch.cuda.is_available()
    if device == 'cuda' and not cuda:
        raise RuntimeError('PyTorch CUDA không khả dụng; dùng --device cpu')
    device = ('cuda' if cuda else 'cpu') if device == 'auto' else device
    if device == 'cpu':
        from app.runtime_selection import require_cpu_memory
        require_cpu_memory()
    dtype = torch.float16 if cuda else torch.float32
    pipe = AutoPipelineForImage2Image.from_pretrained(
        str(model_dir), torch_dtype=dtype, local_files_only=True,
        use_safetensors=True,
    ).to(device)
    image = Image.new('RGB', (512, 512), (185, 197, 200))
    generator = torch.Generator(device='cpu').manual_seed(271)
    output = pipe(
        prompt='Modern office exterior, architectural photography, daylight',
        image=image,
        strength=0.65,
        num_inference_steps=10,
        guidance_scale=6.0,
        generator=generator,
    ).images[0]
    png = output_dir / 'real_sd15_smoke.png'
    output.save(png, format='PNG')
    with Image.open(png) as reopened:
        reopened.verify()
    if png.stat().st_size < 1000:
        raise RuntimeError('PNG generated but is unexpectedly small')
    report = {
        'status': 'PASS_REAL_INFERENCE',
        'engine': 'Diffusers image-to-image',
        'device': device,
        'png': png.name,
        'png_bytes': png.stat().st_size,
        'sha256': hashlib.sha256(png.read_bytes()).hexdigest(),
        'bim_from_image_verified': False,
    }
    (output_dir / 'real_inference_report.json').write_text(
        json.dumps(report, indent=2), encoding='utf-8'
    )
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-dir', default='models/sd15')
    parser.add_argument('--output-dir', default='output/real_inference_smoke')
    parser.add_argument('--device', choices=['cpu', 'cuda', 'auto'], default='auto')
    arguments = parser.parse_args()
    try:
        print(json.dumps(
            run(arguments.model_dir, arguments.output_dir, arguments.device), ensure_ascii=False
        ))
    except Exception as error:
        print('FAIL_REAL_INFERENCE: ' + str(error), file=sys.stderr)
        sys.exit(1)
