"""V86 conservative architecture input checks and CPU-safe settings.

Warn before generation about collage-like or low-quality references; do not
silently alter user geometry or claim a learned detector.
"""
from PIL import Image, ImageOps, ImageStat, ImageFilter


def inspect_reference(image):
    if not isinstance(image, Image.Image):
        return {'ready': False, 'blocking': ['Chưa nạp ảnh'], 'warnings': []}
    source = ImageOps.exif_transpose(image).convert('RGB')
    width, height = source.size
    warnings, blocking = [], []
    if min(width, height) < 256:
        blocking.append('Ảnh quá nhỏ: cạnh ngắn phải từ 256 px')
    if width * height > 40_000_000:
        blocking.append('Ảnh quá lớn: trên 40 megapixel')
    if max(width, height) / max(1, min(width, height)) > 2.8:
        warnings.append('Khung ảnh rất dài: có thể là board/collage; nên crop ảnh chính')
    edge = source.convert('L').filter(ImageFilter.FIND_EDGES)
    edge_mean = ImageStat.Stat(edge).mean[0]
    if edge_mean < 4.0:
        warnings.append('Ít cạnh rõ: ảnh trơn hoặc mờ, khó giữ hình kiến trúc')
    if edge_mean > 45.0:
        warnings.append('Mật độ cạnh rất cao: có thể có bảng chú thích/collage hoặc nhiễu')
    return {'ready': not blocking, 'image_size_px': [width, height],
            'edge_mean': round(edge_mean, 3),
            'blocking': blocking, 'warnings': warnings,
            'collage_detected': False, 'collage_detection_verified': False,
            'note': 'Chỉ kiểm tra ảnh theo quy tắc; cần người dùng duyệt hình khối/crop.'}


def cpu_generation_recommendation(cuda, steps, count, upscale):
    advice = []
    if not cuda:
        if int(steps) > 20:
            advice.append('CPU: ưu tiên 10–20 bước để thử chất lượng đầu vào')
        if int(count) > 1:
            advice.append('CPU: ưu tiên 1 phương án/lượt')
        if int(upscale) > 1:
            advice.append('CPU: phóng lớn truyền thống làm tăng ảnh nhưng không thêm chi tiết AI')
    return advice
