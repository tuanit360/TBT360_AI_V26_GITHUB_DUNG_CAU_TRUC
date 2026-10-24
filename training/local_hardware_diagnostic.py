"""Local Windows hardware diagnostic for the actual T600 4 GiB + RAM 16 GiB target.

Run: python -m training.local_hardware_diagnostic
No model is downloaded, no checkpoint is fabricated, and no training is claimed.
"""
from __future__ import annotations

import ctypes
import json
import platform


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ('dwLength', ctypes.c_ulong),
        ('dwMemoryLoad', ctypes.c_ulong),
        ('ullTotalPhys', ctypes.c_ulonglong),
        ('ullAvailPhys', ctypes.c_ulonglong),
        ('ullTotalPageFile', ctypes.c_ulonglong),
        ('ullAvailPageFile', ctypes.c_ulonglong),
        ('ullTotalVirtual', ctypes.c_ulonglong),
        ('ullAvailVirtual', ctypes.c_ulonglong),
        ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
    ]


def available_memory_gib() -> float | None:
    if platform.system() != 'Windows':
        return None
    info = MEMORYSTATUSEX()
    info.dwLength = ctypes.sizeof(info)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(info)):
        raise OSError('Windows GlobalMemoryStatusEx failed')
    return round(info.ullAvailPhys / 1024 ** 3, 2)


def inspect() -> dict:
    data = {
        'os': platform.system(),
        'available_ram_gib': available_memory_gib(),
        'cuda_available': False,
        'cuda_gpu': None,
        'dedicated_vram_gib': None,
        'real_model_executed': False,
    }
    try:
        import torch
        if torch.cuda.is_available():
            data['cuda_available'] = True
            data['cuda_gpu'] = torch.cuda.get_device_name(0)
            data['dedicated_vram_gib'] = round(
                torch.cuda.get_device_properties(0).total_memory / 1024 ** 3, 2,
            )
    except (ImportError, OSError, RuntimeError) as exc:
        data['torch_diagnostic'] = str(exc)[:160]
    memory = data['available_ram_gib']
    if memory is not None and memory < 5:
        data['recommendation'] = (
            'Close memory-heavy applications and reach about 5 GiB available RAM '
            'before attempting SD1.5 CPU offload on the 4 GiB T600.'
        )
    elif not data['cuda_available']:
        data['recommendation'] = 'Install a compatible CUDA-enabled PyTorch and NVIDIA driver.'
    elif data['dedicated_vram_gib'] < 3.5:
        data['recommendation'] = 'GPU has insufficient dedicated VRAM for the current local SD1.5 profile.'
    else:
        data['recommendation'] = 'Hardware precheck passed; actual SD1.5 inference is still unverified.'
    return data


if __name__ == '__main__':
    print(json.dumps(inspect(), ensure_ascii=False, indent=2))
