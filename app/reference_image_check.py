"""Validate and echo a reference image without involving diffusion weights."""
from PIL import Image, ImageOps


def inspect_reference_image(image):
    if not isinstance(image, Image.Image):
        return None, 'Chưa có ảnh PIL hợp lệ. Hãy tải lại ảnh JPG hoặc PNG.'
    corrected = ImageOps.exif_transpose(image).convert('RGB')
    if corrected.width < 64 or corrected.height < 64:
        return None, 'Ảnh quá nhỏ; cần kích thước tối thiểu 64 x 64 pixel.'
    if corrected.width * corrected.height > 40000000:
        return None, 'Ảnh quá lớn; vui lòng giảm kích thước trước khi kiểm tra.'
    return corrected, (
        f'ĐÃ ĐỌC ẢNH: {corrected.width} x {corrected.height} pixel. '
        'Đây là ảnh đầu vào được kiểm tra, KHÔNG phải ảnh AI tạo.'
    )
