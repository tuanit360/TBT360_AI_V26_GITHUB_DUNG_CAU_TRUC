"""Render diagnostic images through an HTML data URI, avoiding Gradio file URLs.

This is intentionally limited to small diagnostic PNGs. Production generated
images remain files and must satisfy their own serving checks.
"""
import base64
import html
import io
from PIL import Image

def render_diagnostic_image(image):
    if not isinstance(image, Image.Image):
        raise ValueError('Không có ảnh PIL hợp lệ')
    frame = image.convert('RGB')
    frame.thumbnail((640, 480))
    buffer = io.BytesIO()
    frame.save(buffer, format='PNG')
    payload = base64.b64encode(buffer.getvalue()).decode('ascii')
    return (
        '<div style="max-width:640px">'
        '<img alt="Ảnh kiểm tra trực tiếp" style="width:100%;height:auto" '
        'src="data:image/png;base64,' + payload + '">'
        '<p>Đã kết xuất ảnh chẩn đoán trực tiếp, không dùng URL tệp Gradio.</p>'
        '</div>'
    )
