"""Choose a safe AI device without changing the Gradio UI or BIM state."""
import os
import shutil
import subprocess

from app.windows_memory import available_ram_gib

MIN_CPU_FREE_RAM_GIB = 7.0


def _gpu_properties(torch_module):
    properties = torch_module.cuda.get_device_properties(0)
    return round(float(properties.total_memory) / 1024**3, 2)


def inspect_runtime(torch_module, *, environ=None, free_ram_gib=None, gpu_probe=None):
    """Return serializable facts; no pipeline load, UI mutations or CUDA allocation."""
    environ = os.environ if environ is None else environ
    if free_ram_gib is None:
        free_ram_gib = available_ram_gib()
    forced_cpu = environ.get('BIMAI360_FORCE_CPU') == '1'
    torch_version = getattr(torch_module, 'version', None)
    cuda_version = getattr(torch_version, 'cuda', None)
    # Production PyTorch always has torch.version; older regression stubs do
    # not. Trust cuda.is_available() only for those reduced test doubles.
    legacy_stub = torch_version is None
    cuda_build = bool(cuda_version) or legacy_stub
    try:
        cuda_available = bool(torch_module.cuda.is_available()) if cuda_build else False
    except (AssertionError, RuntimeError, OSError):
        cuda_available = False
    vram_gib = None
    if cuda_available:
        try:
            vram_gib = (gpu_probe or (lambda: _gpu_properties(torch_module)))()
        except AttributeError:
            # Reduced legacy test stubs do not implement device properties.
            # Real PyTorch exposes this method; do not invalidate the stub.
            if not legacy_stub:
                cuda_available = False
        except (AssertionError, RuntimeError, OSError, ValueError):
            cuda_available = False
    cpu_ready = free_ram_gib is None or free_ram_gib >= MIN_CPU_FREE_RAM_GIB
    if not forced_cpu and cuda_build and cuda_available:
        mode = 'cuda'
        reason = 'CUDA của PyTorch hoạt động; sử dụng GPU.'
    elif cpu_ready:
        mode = 'cpu'
        reason = ('Chuyển sang CPU vì chưa có CUDA tương thích hoặc chế độ CPU được yêu cầu. '
                  'Tác vụ có thể chạy chậm.')
    else:
        mode = 'blocked'
        reason = ('Không đủ RAM khả dụng để tải model bằng CPU (cần tối thiểu '
                  f'{MIN_CPU_FREE_RAM_GIB:g} GiB); CUDA cũng không sẵn sàng.')
    return {
        'mode': mode, 'reason': reason, 'cuda_torch_build': cuda_build,
        'cuda_available': cuda_available, 'cuda_version': str(
            cuda_version or 'none'),
        'force_cpu': forced_cpu, 'free_ram_gib': free_ram_gib,
        'gpu_vram_gib': vram_gib, 'cpu_ready': cpu_ready,
    }


def require_cpu_memory():
    free = available_ram_gib()
    if free is not None and free < MIN_CPU_FREE_RAM_GIB:
        raise RuntimeError(
            f'Không đủ RAM khả dụng để chuyển sang CPU: còn {free:.2f} GiB, '
            f'cần ít nhất {MIN_CPU_FREE_RAM_GIB:g} GiB. Đã giữ nguyên ảnh, BIM '
            'và log; hãy đóng ứng dụng nặng hoặc dùng CUDA VENV riêng.'
        )
    return free


def nvidia_driver_status(timeout=3):
    binary = shutil.which('nvidia-smi')
    if not binary:
        return {'available': False, 'reason': 'Không tìm thấy nvidia-smi'}
    try:
        output = subprocess.run(
            [binary, '--query-gpu=memory.total,driver_version', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=timeout, check=True,
        )
        return {'available': bool(output.stdout.strip()),
                'summary': output.stdout.strip()[:180]}
    except (subprocess.SubprocessError, OSError):
        return {'available': False, 'reason': 'Không đọc được thông tin driver NVIDIA'}
