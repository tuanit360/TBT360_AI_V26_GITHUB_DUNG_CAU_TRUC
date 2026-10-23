"""Vietnamese, user-facing failure classification for image generation."""
import re


def explain_generation_failure(error):
    message = str(error)
    lowered = message.lower()
    if 'out of memory' in lowered or 'cuda out of memory' in lowered:
        return 'GPU thiếu bộ nhớ. Hãy chọn 1 ảnh, 10–15 bước và bật chế độ tiết kiệm VRAM.'
    if any(value in lowered for value in ('not found in cache', 'local_files_only',
                                           'connection error', 'could not connect',
                                           'repository not found', 'does not appear to have')):
        return 'Chưa tải đủ mô hình sinh ảnh SD1.5. Cần kết nối mạng để tải checkpoint hợp lệ hoặc cài model vào thư mục models.'
    if ('cuda' in lowered and (
        'not available' in lowered or 'driver version is insufficient' in lowered
        or 'no nvidia driver' in lowered or 'cuda driver' in lowered
    )):
        return 'CUDA chưa sẵn sàng. Kiểm tra trình điều khiển NVIDIA hoặc chạy chế độ CPU.'
    if any(value in lowered for value in ('nearly black', 'visually blank')):
        return 'AI trả về ảnh đen hoặc trống. Kết quả đã bị loại; cần kiểm tra VAE, checkpoint và độ chính xác số.'
    if 'ảnh' in lowered or 'tham số' in lowered:
        return message[:350]
    # Do not leak internal filesystem paths, tokens, URLs or traceback to UI.
    return 'Không thể tạo phương án. Mở Tài khoản → Nhật ký hoạt động để xem mã lỗi. Kiểm tra ảnh, GPU và mô hình.'


def has_prompt(brief):
    return isinstance(brief, str) and bool(brief.strip()) and len(brief) <= 2000
