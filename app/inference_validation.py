"""Validate low-cost inference request parameters before expensive loading."""
import math


def validate_inference_parameters(request):
    try:
        count = int(request['count'])
        steps = int(request['steps'])
        seed = int(request['seed'])
        strength = float(request['strength'])
        guidance = float(request['guidance'])
        scale = int(request['scale'])
        sharpness = float(request['sharpness'])
    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        raise ValueError('Invalid inference parameters') from exc
    if not (1 <= count <= 4 and 10 <= steps <= 50):
        raise ValueError('Invalid count or steps')
    if not (0 <= seed < 2**63 - 50):
        raise ValueError('Invalid inference seed')
    if not (math.isfinite(strength) and 0.15 <= strength <= 0.85):
        raise ValueError('Invalid strength')
    if not (math.isfinite(guidance) and 0 <= guidance <= 30):
        raise ValueError('Invalid guidance')
    if scale not in (1, 2, 4):
        raise ValueError('Invalid output scale')
    if not (math.isfinite(sharpness) and 0 <= sharpness <= 1):
        raise ValueError('Invalid sharpening')
    return True
