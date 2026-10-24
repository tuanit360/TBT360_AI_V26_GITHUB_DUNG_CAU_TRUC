"""Display the uploaded image when AI generation cannot run.

This is explicitly an input preview, never an AI output or valid generation
artifact. It uses PIL->inline PNG and does not import torch, CUDA or Gradio.
"""
from PIL import Image
from app.diagnostic_image_render import render_diagnostic_image


def fallback_reference_preview(image, result):
    """Preserve error details and refuse to create an artificial AI ZIP."""
    markup, archive, status, log = result
    if archive is not None or not isinstance(image, Image.Image):
        return result
    try:
        preview = render_diagnostic_image(image, max_side=768)
    except (OSError, ValueError, TypeError):
        return result
    label = (
        '<p><strong>Chỉ hiển thị ảnh tham chiếu gốc — KHÔNG PHẢI ẢNH AI.</strong>'
        ' Sinh ảnh mới không thành công; xem trạng thái và nhật ký bên dưới.</p>'
    )
    return label + preview, None, status, log
