"""Vietnamese, user-facing failure classification for image generation."""
import re


def explain_generation_failure(error):
    message = str(error)
    lowered = message.lower()
    if 'bimai360_cpu_ram_low' in lowered:
        return ('RAM khả dụng không đủ để sinh ảnh AI bằng CPU. '
                'Đóng bớt ứng dụng, hoặc sử dụng môi trường CUDA VENV đã kiểm tra. '
                'Ảnh tham chiếu vẫn xem được và không phải kết quả AI.')
    if 'bimai360_cpu_selected' in lowered:
        return ('Phiên bản hiện tại chạy CPU, không có CUDA. '
                'Hãy kiểm tra model SD1.5 và RAM; không cần sửa driver NVIDIA '
                'để xem ảnh tham chiếu hoặc chạy CPU.')
    if 'out of memory' in lowered or 'cuda out of memory' in lowered:
        return 'GPU thiếu bộ nhớ. Hãy chọn 1 ảnh, 10–15 bước và bật chế độ tiết kiệm VRAM.'
    if any(value in lowered for value in ('not found in cache', 'local_files_only',
                                           'connection error', 'could not connect',
                                           'repository not found', 'does not appear to have')):
        return 'Chưa tải đủ mô hình sinh ảnh SD1.5. Cần kết nối mạng để tải checkpoint hợp lệ hoặc cài model vào thư mục models.'
    if ('torch not compiled with cuda enabled' in lowered
            or 'cuda is not available in this build' in lowered
            or 'pytorch was compiled without cuda support' in lowered):
        return ('Bản BIMAI360 đang chạy dùng PyTorch CPU, không có CUDA. '
                'GPU NVIDIA T600 vẫn có thể hoạt động bình thường; '
                'hãy dùng launcher CPU hoặc môi trường Python CUDA riêng. '
                'Không cần cài lại driver chỉ vì lỗi này.')
    if ('cuda' in lowered and (
        'not available' in lowered or 'driver version is insufficient' in lowered
        or 'no nvidia driver' in lowered or 'cuda driver' in lowered
    )):
        return 'CUDA chưa sẵn sàng. Kiểm tra trình điều khiển NVIDIA hoặc chạy chế độ CPU.'
    if any(value in lowered for value in (
        'generated zip', 'zip archive', 'output image',
    )):
        return ('Ảnh hoặc gói ZIP kết quả bị thiếu/hỏng. '
                'Kết quả không được đánh dấu thành công; hãy thử tạo lại '
                'và xem logs/runtime_errors.log nếu lỗi tiếp diễn.')
    if 'permission denied' in lowered or 'access is denied' in lowered:
        return ('Không có quyền ghi thư mục dữ liệu. '
                'Hãy giải nén Portable ra thư mục cá nhân có quyền ghi '
                'và không chạy trực tiếp trong ZIP.')
    if any(value in lowered for value in ('nearly black', 'visually blank')):
        return 'AI trả về ảnh đen hoặc trống. Kết quả đã bị loại; cần kiểm tra VAE, checkpoint và độ chính xác số.'
    if 'ảnh' in lowered or 'tham số' in lowered:
        return message[:350]
    # Do not leak internal filesystem paths, tokens, URLs or traceback to UI.
    return 'Không thể tạo phương án. Xem logs/runtime_errors.log hoặc dùng MO_LOG_KHONG_CAN_UI.bat; kiểm tra ảnh, GPU và mô hình.'


def has_prompt(brief):
    return isinstance(brief, str) and bool(brief.strip()) and len(brief) <= 2000
