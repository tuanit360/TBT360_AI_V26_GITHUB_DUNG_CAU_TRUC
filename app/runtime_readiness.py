"""Guard AI model loading independently of Gradio, CUDA and model cache."""
import os
from app.runtime_selection import inspect_runtime


def check_generation_runtime(torch_module, *, environ=None, free_ram_gib=None):
    """Preflight returns a stable, user-facing result before loading Diffusers."""
    environ = os.environ if environ is None else environ
    selected = inspect_runtime(
        torch_module, environ=environ, free_ram_gib=free_ram_gib,
    )
    if selected['mode'] == 'blocked':
        available = selected['free_ram_gib']
        display = 'không xác định' if available is None else f'{available:.2f} GiB'
        return {
            'ready': False, 'device': 'none',
            'message': (
                'BIMAI360_CPU_RAM_LOW: RAM khả dụng ' + display
                + '. Cần ít nhất 7 GiB để thử tải model SD1.5 bằng CPU. '
                'Không thể tự chuyển sang CUDA nếu PyTorch không hỗ trợ.'
            ),
        }
    return {
        'ready': True, 'device': selected['mode'],
        'message': ('Đã chọn GPU CUDA tương thích.' if selected['mode'] == 'cuda'
                    else 'Đã chọn CPU: không yêu cầu CUDA để chạy.'),
    }
