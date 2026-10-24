"""Privacy-safe worker failure handoff, independent of Gradio and PyTorch."""
import json
from pathlib import Path


def classify_worker_failure(exc):
    message = str(exc).lower()
    if any(token in message for token in (
        'out of memory', 'not enough memory', 'cannot allocate memory'
    )):
        code = 'OUT_OF_MEMORY'
        user_message = 'Không đủ RAM/VRAM để sinh ảnh. Thử CPU và đóng ứng dụng nặng.'
    elif any(token in message for token in (
        'model_index.json', 'checkpoint', 'not found in cache',
        'local_files_only', 'repository not found'
    )):
        code = 'MODEL_MISSING'
        user_message = 'Thiếu hoặc lỗi checkpoint SD1.5. Kiểm tra models/sd15.'
    elif any(token in message for token in ('cuda', 'nvidia driver')):
        code = 'CUDA_UNAVAILABLE'
        user_message = 'Runtime CUDA không sử dụng được. Hãy thử môi trường CPU.'
    elif isinstance(exc, (ValueError, TypeError)):
        code = 'INVALID_INPUT_OR_OUTPUT'
        user_message = 'Đầu vào hoặc kết quả AI không hợp lệ; xem log worker.'
    else:
        code = 'WORKER_EXCEPTION'
        user_message = 'Tiến trình AI gặp lỗi; xem image_worker.log.'
    return {'schema': 'bimai360.worker_failure.v1',
            'status': 'FAILED', 'code': code, 'message': user_message}


def read_safe_worker_failure(file_path):
    path = Path(file_path)
    messages = {
        'OUT_OF_MEMORY': 'Không đủ RAM hoặc VRAM.',
        'MODEL_MISSING': 'Checkpoint SD1.5 thiếu hoặc không hợp lệ.',
        'CUDA_UNAVAILABLE': 'CUDA không hoạt động; có thể sử dụng CPU.',
        'INVALID_INPUT_OR_OUTPUT': 'Đầu vào hoặc đầu ra AI không hợp lệ.',
        'WORKER_EXCEPTION': 'Worker AI gặp lỗi Python.',
    }
    try:
        if path.stat().st_size > 2048:
            return 'Không đọc được báo cáo lỗi worker.'
        result = json.loads(path.read_text(encoding='utf-8'))
        if result.get('schema') != 'bimai360.worker_failure.v1':
            return 'Báo cáo worker không hợp lệ.'
        return messages.get(result.get('code'), 'Lỗi worker không xác định.')
    except (OSError, ValueError, TypeError):
        return 'Không có báo cáo lỗi worker; có thể tiến trình bị dừng đột ngột.'
