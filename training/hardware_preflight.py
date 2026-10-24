"""GPU suitability probe for training and VLM, with no false PASS.

CPU-only Windows Portable is always allowed to run the UI. Training needs
a configured GPU runner and enough VRAM for the selected model.
"""
import json


def summarize_hardware(cuda_available, vram_gib=None, gpu_name='unknown'):
    if not isinstance(cuda_available, bool):
        raise ValueError('CUDA availability must be boolean')
    if cuda_available and (type(vram_gib) not in (int, float) or vram_gib <= 0):
        raise ValueError('GPU VRAM measurement required')
    small = cuda_available and vram_gib < 8
    return {
        'gpu_name': gpu_name,
        'cuda_available': cuda_available,
        'vram_gib': round(vram_gib, 2) if cuda_available else None,
        'windows_portable_cpu_available': True,
        'gpu_training_ready': cuda_available and vram_gib >= 8,
        'sd15_lora_8g_preflight': 'eligible_for_trial' if cuda_available and vram_gib >= 8 else 'blocked',
        'architecture_vlm_finetuning': 'not_verified',
        'reason': ('CPU or no compatible CUDA GPU' if not cuda_available else
                   'Less than 8 GiB VRAM; train on remote GPU' if small else
                   'Hardware preflight only; must still execute training and evaluate model'),
    }


def probe_cuda():
    import torch
    available = torch.cuda.is_available()
    properties = torch.cuda.get_device_properties(0) if available else None
    return summarize_hardware(
        available,
        properties.total_memory / 2**30 if properties else None,
        torch.cuda.get_device_name(0) if available else 'none',
    )


if __name__ == '__main__':
    print(json.dumps(probe_cuda(), ensure_ascii=False, indent=2))
