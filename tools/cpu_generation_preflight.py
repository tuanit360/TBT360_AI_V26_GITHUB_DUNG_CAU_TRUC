"""CPU image-generation readiness: no model load, download or Gradio startup."""
import importlib
from pathlib import Path

from app.cpu_readiness import inspect_local_assets
from app.windows_memory import available_ram_gib

MIN_RAM_GIB = 7.0


def build_cpu_preflight_report(root, *, torch_module=None, free_ram_gib=None):
    """Check actual CPU prerequisites without claiming inference succeeded."""
    root = Path(root)
    report = {
        'schema': 'bimai360.cpu_generation_preflight.v279',
        'ready': False,
        'cpu_torch_available': False,
        'ram_gib': None,
        'ram_ok': False,
        'local_model_ready': False,
        'offline_model_required': False,
        'issues': [],
        'note': 'Preflight only; no inference was executed.',
    }
    if free_ram_gib is None:
        try:
            free_ram_gib = available_ram_gib()
        except OSError:
            report['issues'].append('Không đọc được RAM khả dụng.')
    report['ram_gib'] = free_ram_gib
    report['ram_ok'] = free_ram_gib is None or free_ram_gib >= MIN_RAM_GIB
    if not report['ram_ok']:
        report['issues'].append(
            f'RAM khả dụng {free_ram_gib:.2f} GiB, cần ít nhất 7 GiB để tải CPU SD1.5.'
        )
    try:
        torch = torch_module if torch_module is not None else importlib.import_module('torch')
        report['cpu_torch_available'] = hasattr(torch, 'float32') and hasattr(torch, 'Generator')
        if not report['cpu_torch_available']:
            report['issues'].append('PyTorch chưa đủ thành phần để sinh ảnh CPU.')
    except (ImportError, OSError, RuntimeError) as exc:
        report['issues'].append('Không nạp được PyTorch: ' + type(exc).__name__)
    # An absent local model is not a failure when online downloads are permitted,
    # but never report an offline model as ready without checking its components.
    assets = inspect_local_assets(root)
    report['local_model_ready'] = bool(assets['model_files_complete'])
    report['offline_model_required'] = __import__('os').environ.get('TBT360_OFFLINE') == '1'
    if report['offline_model_required'] and not report['local_model_ready']:
        report['issues'].append('Offline thiếu checkpoint SD1.5 đầy đủ.')
    if not report['local_model_ready'] and not report['offline_model_required']:
        report['issues'].append('Model chưa có tại chỗ; cần tải khi chạy lần đầu (không xác nhận mạng).')
    report['ready'] = bool(
        report['ram_ok'] and report['cpu_torch_available']
        and (not report['offline_model_required'] or report['local_model_ready'])
    )
    return report
