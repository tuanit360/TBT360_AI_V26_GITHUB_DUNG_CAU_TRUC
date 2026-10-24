"""Use existing Diffusers CPU offload when CUDA VRAM is small."""
import gc


def gpu_memory_gib(torch_module):
    try:
        return float(torch_module.cuda.get_device_properties(0).total_memory) / (1024 ** 3)
    except (AttributeError, AssertionError, RuntimeError, ValueError, OSError):
        return None


def choose_device_mode(device, memory_mode, vram_gib):
    if device != 'cuda':
        return 'cpu'
    if memory_mode == 'Tiết kiệm VRAM tối đa':
        return 'sequential_offload'
    # SD1.5 weights + activations are unreliable fully resident on a
    # 4 GiB workstation GPU. Offload avoids forcing allocation there.
    if vram_gib is not None and vram_gib < 6:
        return 'sequential_offload'
    return 'cuda'


def configure_pipeline_device(pipeline, torch_module, device, memory_mode):
    strategy = choose_device_mode(
        device, memory_mode, gpu_memory_gib(torch_module)
    )
    if strategy == 'sequential_offload':
        if not hasattr(pipeline, 'enable_sequential_cpu_offload'):
            raise RuntimeError('Diffusers CPU offload unavailable')
        pipeline.enable_sequential_cpu_offload()
    else:
        pipeline.to('cpu' if strategy == 'cpu' else 'cuda')
    return strategy
