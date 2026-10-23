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
          seed: int = 42, steps: int = 15,
          reference: Path | None = None, strength: float = 0.4) -> dict:
    if reference is not None and not 0 < strength <= 1:
        raise ValueError('img2img strength must be in (0, 1]')
    if not 1 <= steps <= 100:
        raise ValueError('steps must be 1..100')
    # Diffusers img2img truncates steps * strength to an integer. A zero
    # denoising-step run must not be reported as successful inference.
    if reference is not None and int(steps * strength) < 1:
        raise ValueError('img2img needs at least one denoising step; increase strength or steps')
    if not prompt.strip():
        raise ValueError('A nonempty architectural prompt is required')
    if not model or not model.strip():
        raise ValueError('A real base model is required')
    if output.exists():
        raise FileExistsError('Refusing to overwrite an existing image')
    # Validate the reference before loading multi-GB model weights.
    if reference is not None:
        from PIL import Image, ImageOps
        reference = Path(reference).resolve()
        with Image.open(reference) as source:
            source.verify()
        with Image.open(reference) as source:
            if source.width < 128 or source.height < 128:
                raise ValueError('Reference image is too small for architectural img2img')
            prepared_reference = ImageOps.pad(
                ImageOps.exif_transpose(source).convert('RGB'), (512, 512),
            )
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
    if reference is not None:
        from diffusers import StableDiffusionImg2ImgPipeline

    if device == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable')
    generator = torch.Generator(device=device).manual_seed(seed)
    pipeline_class = (
        StableDiffusionImg2ImgPipeline if reference is not None
        else StableDiffusionPipeline
    )
    pipeline = pipeline_class.from_pretrained(
        model, torch_dtype=torch.float16 if device == 'cuda' else torch.float32,
    )
    try:
        pipeline.to(device)
        pipeline.load_lora_weights(
            str(Path(adapter).resolve()),
            weight_name='pytorch_lora_weights.safetensors',
        )
        generation_args = {
            'prompt': prompt,
            'num_inference_steps': steps,
            'generator': generator,
        }
        reference_sha256 = None
        if reference is not None:
            reference = Path(reference)
            with reference.open('rb') as stream:
                reference_sha256 = hashlib.file_digest(stream, 'sha256').hexdigest()
            generation_args.update({
                'image': prepared_reference, 'strength': strength,
            })
        else:
            generation_args.update({'width': 512, 'height': 512})
        generated = pipeline(**generation_args).images[0]
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
        'generation_mode': 'img2img' if reference is not None else 'text2img',
        'reference_sha256': reference_sha256,
        'reference_image': str(reference.resolve()) if reference is not None else None,
        'strength': strength if reference is not None else None,
        'reference_geometry_verified': False,
    }


def write_evidence(report_path: Path, result: dict) -> None:
    """Exclusive report write; incomplete reports are never kept as evidence."""
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open('x', encoding='utf-8') as stream:
        try:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.flush()
        except Exception:
            stream.close()
            report_path.unlink(missing_ok=True)
            raise


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
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--strength', type=float, default=0.4)
    args = parser.parse_args()
    if args.image.resolve() == args.report.resolve():
        parser.error('--image and --report must be different paths')
    if args.report.exists():
        parser.error('--report already exists; use a new path to preserve prior evidence')
    try:
        result = infer(args.adapter, args.model, args.image, args.device,
                       args.prompt, args.seed, args.steps,
                       args.reference, args.strength)
    except Exception as exc:
        result = {'status': 'FAILED', 'error': f'{type(exc).__name__}: {exc}'[:300]}
    write_evidence(args.report, result)
    print(json.dumps(result, ensure_ascii=False))
    if result['status'] != 'DIFFUSERS_INFERENCE_EXECUTED_NOT_QUALITY_VERIFIED':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
