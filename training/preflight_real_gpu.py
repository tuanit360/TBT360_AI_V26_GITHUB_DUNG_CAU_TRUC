"""Fail fast on missing dependencies for the real SD1.5 GPU training/inference job.

This preflight cannot prove a model download, training, or inference occurred.
"""
import argparse
import importlib
import json
import shutil
from pathlib import Path


def check_gpu_environment(dataset='dataset/v72_certified', min_free_gib=15,
                          min_vram_gib=3.5):
    checks = {}
    for module in ('torch', 'diffusers', 'transformers', 'accelerate',
                   'safetensors', 'PIL', 'datasets'):
        try:
            importlib.import_module(module)
            checks[module] = 'available'
        except (ImportError, OSError) as exc:
            return {'ready': False, 'reason': f'{module} unavailable: {exc}'[:240],
                    'checks': checks}
    import torch
    if not torch.cuda.is_available():
        return {'ready': False, 'reason': 'CUDA GPU not available', 'checks': checks}
    vram_gib = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
    if vram_gib < min_vram_gib:
        return {'ready': False,
                'reason': f'CUDA GPU VRAM {vram_gib:.1f} GiB below {min_vram_gib} GiB minimum',
                'checks': checks}
    free = shutil.disk_usage(Path.cwd()).free / (1024 ** 3)
    if free < min_free_gib:
        return {'ready': False, 'reason': f'Insufficient disk space: {free:.1f} GiB free',
                'checks': checks}
    from training.gated_dataset import verify
    try:
        certificate = verify(Path(dataset))
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        return {'ready': False, 'reason': f'Certified dataset invalid: {exc}'[:240],
                'checks': checks}
    profile = 'low_vram_256' if vram_gib < 8 else 'standard_512'
    return {
        'ready': True, 'checks': checks,
        'training_profile': profile,
        'gpu_name': torch.cuda.get_device_name(0),
        'free_disk_gib': round(free, 2),
        'gpu_vram_gib': round(vram_gib, 2),
        'dataset_verified': True,
        'real_inference_performed': False,
        'real_training_performed': False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', default='dataset/v72_certified')
    args = parser.parse_args()
    result = check_gpu_environment(args.dataset)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result['ready']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
