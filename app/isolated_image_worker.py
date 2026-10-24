"""Standalone image-to-image worker. No Gradio/UI import in this process."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback
import zipfile


def run_job(job_file):
    from PIL import Image, ImageOps
    from app.worker_evidence import write_state
    request_path = Path(job_file).resolve()
    request = json.loads(request_path.read_text(encoding='utf-8'))
    if request.get('schema') != 'bimai360.worker.v1':
        raise ValueError('Invalid worker request')
    root = request_path.parent.parent.parent
    run_dir = request_path.parent
    job_id = run_dir.name.removeprefix('isolated_')
    write_state(root, job_id, 'BOOT')
    source_path = run_dir / 'reference_input.png'
    if not source_path.is_file():
        raise ValueError('Missing reference image')
    steps = int(request['steps'])
    if not 10 <= steps <= 50:
        raise ValueError('Invalid inference steps')
    strength = float(request['strength'])
    if not 0.15 <= strength <= 0.85:
        raise ValueError('Invalid image strength')
    seed = int(request['seed'])
    prompt = str(request['prompt'])
    negative = str(request['negative'])
    if len(prompt) > 4000 or len(negative) > 2000:
        raise ValueError('Prompt too long')
    os.environ['BIMAI360_HOME'] = str(root)
    from app.generation_stage import write_generation_stage
    write_generation_stage(root, 'MODEL_LOAD', 'BEGIN')
    write_state(root, job_id, 'TORCH_IMPORT_BEGIN')
    import torch
    write_state(root, job_id, 'TORCH_IMPORT_DONE')
    from app.runtime_readiness import check_generation_runtime
    selected = check_generation_runtime(torch)
    if not selected['ready']:
        raise RuntimeError(selected['message'])
    device = selected['device']
    write_state(root, job_id, 'DIFFUSERS_IMPORT_BEGIN')
    from diffusers import AutoPipelineForImage2Image
    write_state(root, job_id, 'DIFFUSERS_IMPORT_DONE')
    local = root / 'models' / 'sd15'
    if not (local / 'model_index.json').is_file():
        if os.environ.get('TBT360_OFFLINE') == '1':
            raise RuntimeError('Thiếu checkpoint SD1.5 offline.')
        model = 'stable-diffusion-v1-5/stable-diffusion-v1-5'
    else:
        model = str(local)
    dtype = torch.float16 if device == 'cuda' else torch.float32
    write_state(root, job_id, 'MODEL_LOAD_BEGIN')
    pipeline = AutoPipelineForImage2Image.from_pretrained(
        model, torch_dtype=dtype, use_safetensors=True,
        local_files_only=os.environ.get('TBT360_OFFLINE') == '1',
        cache_dir=str(root / 'models'),
    )
    if device == 'cuda' and request.get('memory_mode') == 'Tiết kiệm VRAM tối đa':
        pipeline.enable_sequential_cpu_offload()
    else:
        pipeline.to(device)
    write_generation_stage(root, 'MODEL_LOAD', 'DONE')
    write_state(root, job_id, 'MODEL_LOAD_DONE')
    lora_name = str(request.get('lora', 'Không dùng LoRA'))
    if lora_name != 'Không dùng LoRA':
        from app.lora_validation import verified_adapters
        if lora_name not in verified_adapters(root / 'loras'):
            raise ValueError('LoRA không hợp lệ; không thay đổi model.')
        pipeline.load_lora_weights(
            str(root / 'loras' / lora_name),
            weight_name='pytorch_lora_weights.safetensors',
        )
    write_generation_stage(root, 'LORA', 'DONE')
    sizes = {'Vuông 1:1': (512, 512), 'Ngang 4:3': (576, 448),
             'Ngang 3:2': (640, 448), 'Dọc 3:4': (448, 576),
             'Dọc 2:3': (448, 640)}
    aspect = request['aspect']
    if aspect not in sizes:
        raise ValueError('Invalid aspect')
    with Image.open(source_path) as original:
        source = ImageOps.exif_transpose(original).convert('RGB')
        if request.get('fit_mode') == 'Cắt đầy khung':
            source = ImageOps.fit(source, sizes[aspect], method=Image.Resampling.LANCZOS)
        else:
            source = ImageOps.pad(
                source, sizes[aspect], color=(230, 231, 230),
                method=Image.Resampling.LANCZOS)
    from app.generated_image_gate import validate_generated_image
    from app.atomic_export import publish_directory_zip
    from PIL import ImageFilter
    images = []
    for index in range(int(request['count'])):
        write_state(root, job_id, 'INFERENCE_BEGIN')
        write_generation_stage(root, 'INFERENCE', f'BEGIN image={index+1}')
        generator = torch.Generator(device='cpu').manual_seed(seed + index)
        result = pipeline(
            prompt=prompt, negative_prompt=negative, image=source,
            strength=strength, guidance_scale=float(request['guidance']),
            num_inference_steps=steps, generator=generator,
        ).images[0]
        write_generation_stage(root, 'INFERENCE', f'DONE image={index+1}')
        write_state(root, job_id, 'INFERENCE_DONE')
        factor = int(request['scale'])
        if factor not in (1, 2, 4):
            raise ValueError('Invalid postprocessing scale')
        result = result.convert('RGB')
        if factor != 1:
            result = result.resize(
                (result.width * factor, result.height * factor),
                Image.Resampling.LANCZOS)
        sharpness = float(request['sharpness'])
        if not 0 <= sharpness <= 1:
            raise ValueError('Invalid sharpening')
        if sharpness:
            result = result.filter(ImageFilter.UnsharpMask(
                radius=0.9, percent=int(45 * sharpness), threshold=4))
        validate_generated_image(
            result, prepared_input=source if factor == 1 else None,
            expected_size=(source.width * factor, source.height * factor),
        )
        filename = f'architecture_option_{index+1:02d}_seed_{seed+index}.png'
        write_generation_stage(root, 'PNG_SAVE', f'BEGIN image={index+1}')
        write_state(root, job_id, 'PNG_SAVE_BEGIN')
        result.save(run_dir / filename, format='PNG')
        with Image.open(run_dir / filename) as verified:
            verified.verify()
        write_generation_stage(root, 'PNG_SAVE', f'DONE image={index+1}')
        write_state(root, job_id, 'PNG_SAVE_DONE')
        images.append((str(run_dir / filename), f'Phương án {index+1} · seed {seed+index}'))
    manifest = {'schema': 'bimai360.isolated.v1', 'device': device,
                'seed': seed, 'steps': steps,
                'files': [Path(file).name for file, _ in images]}
    (run_dir / 'generation.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    # Do not put the raw job payload or reference input into generated outputs.
    for source_file in (request_path, source_path):
        if source_file.is_file():
            source_file.unlink()
    archive = run_dir.with_suffix('.zip')
    write_generation_stage(root, 'ZIP_EXPORT', 'BEGIN')
    write_state(root, job_id, 'ZIP_EXPORT_BEGIN')
    publish_directory_zip(run_dir, archive)
    write_state(root, job_id, 'ZIP_EXPORT_DONE')
    write_generation_stage(root, 'ZIP_EXPORT', 'DONE')
    report = {'status': 'PASS_REAL_INFERENCE', 'images': images,
              'archive': str(archive), 'device': device,
              'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}
    write_state(root, job_id, 'DONE', 'COMPLETED')
    (run_dir / 'worker_result.json').write_text(
        json.dumps(report, ensure_ascii=False), encoding='utf-8')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--job', required=True)
    arguments = parser.parse_args(argv)
    try:
        run_job(arguments.job)
        return 0
    except Exception as exc:
        traceback.print_exc()
        # Write a small bounded status atomically. Never expose raw traceback,
        # prompts, user paths or environment data to the browser.
        try:
            from app.worker_failure import classify_worker_failure
            job_path = Path(arguments.job).resolve()
            failure = classify_worker_failure(exc)
            from app.worker_evidence import write_state
            write_state(
                job_path.parent.parent.parent,
                job_path.parent.name.removeprefix('isolated_'),
                'FAILED', 'FAILED', failure['code'],
            )
            target = job_path.parent / 'worker_failure.json'
            partial = target.with_suffix('.json.part')
            partial.write_text(
                json.dumps(failure, ensure_ascii=False), encoding='utf-8'
            )
            os.replace(partial, target)
        except (OSError, ValueError, ImportError):
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
