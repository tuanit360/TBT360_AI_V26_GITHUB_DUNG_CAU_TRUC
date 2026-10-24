"""Cheap checkpoint sanity checks before importing SD weights."""
import json
from pathlib import Path


def validate_sd15_index(directory):
    root = Path(directory)
    index = root / 'model_index.json'
    if not index.is_file() or index.stat().st_size > 128 * 1024:
        raise ValueError('SD1.5 model_index.json missing or oversized')
    try:
        document = json.loads(index.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise ValueError('SD1.5 model_index.json is invalid') from exc
    if not isinstance(document, dict):
        raise ValueError('SD1.5 index must be an object')
    # Require an image-generation checkpoint structure, not merely an
    # arbitrarily named JSON file. Components are validated by Diffusers.
    components = ('unet', 'vae', 'scheduler', 'text_encoder', 'tokenizer')
    missing = [key for key in components if key not in document]
    if missing:
        raise ValueError('SD1.5 index missing components: ' + ', '.join(missing))
    return True
