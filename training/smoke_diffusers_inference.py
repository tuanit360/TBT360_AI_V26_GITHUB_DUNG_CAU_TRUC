"""Execute a real SD1.5 + LoRA image-generation smoke on a configured machine.

No model downloads or fake image artifacts are performed in regular CI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path



def infer(adapter: Path, model: str, output: Path, device: str = 'cpu',
          prompt: str = 'Architectural photograph of a modern office facade',
          seed: int = 42, steps: int = 15) -> dict:
    if not 1 <= steps <= 100:
        raise ValueError('steps must be 1..100')
    if not prompt.strip():
        raise ValueError('A nonempty architectural prompt is required')
    if not model or not model.strip():
        raise ValueError('A real base model is required')
    if output.exists():
        raise FileExistsError('Refusing to overwrite an existing image')
    # Validate adapter before model loading. Only actual output is a success.
    from app.lora_validation import validate_adapter
    certificate = validate_adapter(adapter)
    if not certificate['valid']:
        raise ValueError('Invalid adapter: ' + certificate['reason'])
    if device not in ('cpu', 'cuda'):
        raise ValueError('Unsupported device')
    import torch
    from PIL import Image
    from diffusers import StableDiffusionPipeline

    if device == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable')
    generator = torch.Generator(device=device).manual_seed(seed)
    pipeline = StableDiffusionPipeline.from_pretrained(
        model, torch_dtype=torch.float16 if device == 'cuda' else torch.float32,
    )
    try:
        pipeline.to(device)
        pipeline.load_lora_weights(
            str(Path(adapter).resolve()),
            weight_name='pytorch_lora_weights.safetensors',
        )
        generated = pipeline(
            prompt=prompt, num_inference_steps=steps, generator=generator,
            width=512, height=512,
        ).images[0]
        from app.generated_image_gate import validate_generated_image
        image_evidence = validate_generated_image(generated, expected_size=(512, 512))
        output.parent.mkdir(parents=True, exist_ok=True)
        # Do not leave incomplete outputs claiming a successful inference.
        # Exclusive creation must happen outside cleanup handling: if another
        # process created the destination meanwhile, never delete its file.
        with output.open('xb') as stream:
            try:
                generated.save(stream, format='PNG')
            except Exception:
                # On Windows the handle must be closed before unlinking.
                stream.close()
                output.unlink(missing_ok=True)
                raise
        try:
            with Image.open(output) as verified:
                verified.verify()
        except Exception:
            output.unlink(missing_ok=True)
            raise
    finally:
        del pipeline
    # Stream the generated output for large files; do not load it all into RAM.
    with output.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {
        'status': 'DIFFUSERS_INFERENCE_EXECUTED_NOT_QUALITY_VERIFIED',
        'image': str(output),
        'image_sha256': digest,
        'adapter_sha256': certificate['sha256'],
        'model': model,
        'prompt': prompt,
        'seed': seed,
        'steps': steps,
        'device': device,
        'quality_evaluated': False,
        'basic_image_gate': image_evidence,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--adapter', required=True, type=Path)
    parser.add_argument('--model', required=True)
    parser.add_argument('--image', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--device', choices=('cpu', 'cuda'), default='cpu')
    parser.add_argument('--prompt', default='Architectural photograph of a modern office facade')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--steps', type=int, default=15)
    args = parser.parse_args()
    if args.image.resolve() == args.report.resolve():
        parser.error('--image and --report must be different paths')
    if args.report.exists():
        parser.error('--report already exists; use a new path to preserve prior evidence')
    try:
        result = infer(args.adapter, args.model, args.image, args.device,
                       args.prompt, args.seed, args.steps)
    except Exception as exc:
        result = {'status': 'FAILED', 'error': f'{type(exc).__name__}: {exc}'[:300]}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x', encoding='utf-8') as report_stream:
        json.dump(result, report_stream, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False))
    if result['status'] != 'DIFFUSERS_INFERENCE_EXECUTED_NOT_QUALITY_VERIFIED':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
