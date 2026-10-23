"""Release-blocking quality gate for black or corrupt generated images.

Does not invent an AI success result. It rejects unusable outputs and
records evidence for diagnostics, rather than displaying black cards.
"""
from PIL import Image, ImageStat


def _percentile_level(histogram, fraction, total):
    target = max(1, int(total * fraction))
    seen = 0
    for level, frequency in enumerate(histogram):
        seen += frequency
        if seen >= target:
            return level
    return 255



def validate_generated_image(image, prepared_input=None, expected_size=None):
    if not isinstance(image, Image.Image):
        raise ValueError('AI returned no usable image')
    rgb = image.convert('RGB')
    if rgb.width < 128 or rgb.height < 128:
        raise ValueError('AI image dimensions are too small')
    if expected_size is not None and rgb.size != tuple(expected_size):
        raise ValueError('Generated image size does not match requested export dimensions')
    if prepared_input is not None:
        reference = prepared_input.convert('RGB')
        if reference.size != rgb.size:
            raise ValueError('Model output size does not match prepared input')
    stat = ImageStat.Stat(rgb)
    mean_brightness = sum(stat.mean) / 3.0
    dynamic_range = max(channel[1] for channel in stat.extrema) - min(
        channel[0] for channel in stat.extrema)
    # Extrema alone can be fooled by a single hot pixel in an otherwise
    # blank image. Check robust luminance variation across the image.
    luminance = rgb.convert('L')
    histogram = luminance.histogram()
    pixel_count = rgb.width * rgb.height
    robust_range = (
        _percentile_level(histogram, 0.99, pixel_count)
        - _percentile_level(histogram, 0.01, pixel_count)
    )
    if mean_brightness < 12 or dynamic_range < 6 or robust_range < 5:
        raise ValueError(
            'AI output is nearly black or visually blank. '
            'Check VAE, model weights, numerical precision and CUDA driver; '
            'the result was rejected rather than delivered as a valid design.')
    return {
        'width': rgb.width,
        'height': rgb.height,
        'mean_brightness': round(mean_brightness, 3),
        'dynamic_range': dynamic_range,
        'robust_luminance_range': robust_range,
        'black_output_rejected': False,
        'visual_design_verified': False,
    }
