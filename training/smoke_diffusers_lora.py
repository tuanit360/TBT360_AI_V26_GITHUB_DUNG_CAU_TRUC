"""Real Diffusers LoRA load smoke: run only with an actual SD1.5 checkpoint.

This is an optional GPU/CPU test, not an image-quality benchmark. No mock PASS.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.lora_validation import validate_adapter


def smoke_load(adapter_path: Path, model_path: str, device: str = 'cpu') -> dict:
    adapter_path = Path(adapter_path).resolve()
    structural = validate_adapter(adapter_path)
    if not structural['valid']:
        raise ValueError('Adapter structural gate rejected: ' + structural['reason'])
    if device not in ('cpu', 'cuda'):
        raise ValueError('device must be cpu or cuda')
    import torch
    from diffusers import StableDiffusionPipeline

    if not model_path or not model_path.strip():
        raise ValueError('Real base model path or model identifier required')
    if device == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; cannot claim CUDA load PASS')
    dtype = torch.float16 if device == 'cuda' else torch.float32
    pipeline = StableDiffusionPipeline.from_pretrained(
        model_path, torch_dtype=dtype,
    )
    try:
        pipeline.to(device)
        pipeline.load_lora_weights(
            str(adapter_path), weight_name='pytorch_lora_weights.safetensors',
        )
        return {
            'status': 'DIFFUSERS_LOAD_PASS_NOT_INFERENCE',
            'adapter_sha256': structural['sha256'],
            'base_model': model_path,
            'device': device,
            'generated_images': 0,
            'quality_evaluated': False,
            'inference_verified': False,
            'checkpoint_structural_verified': True,
        }
    finally:
        del pipeline


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--adapter', required=True, type=Path)
    parser.add_argument('--model', required=True)
    parser.add_argument('--device', choices=('cpu', 'cuda'), default='cpu')
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = smoke_load(args.adapter, args.model, args.device)
    except Exception as exc:
        result = {'status': 'FAILED', 'error': f'{type(exc).__name__}: {exc}'[:300]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
    if result['status'] != 'DIFFUSERS_LOAD_PASS_NOT_INFERENCE':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
