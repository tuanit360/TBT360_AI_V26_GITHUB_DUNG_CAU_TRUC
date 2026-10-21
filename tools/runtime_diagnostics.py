"""Dependency and data checks. No model download; safe to run offline."""
from pathlib import Path
import importlib
import os
import sys

REQUIRED = ('torch', 'diffusers', 'transformers', 'gradio', 'safetensors', 'PIL')


def diagnostic_report(root):
    root = Path(root)
    missing = []
    versions = {}
    for module in REQUIRED:
        try:
            obj = importlib.import_module(module)
            versions[module] = str(getattr(obj, '__version__', 'installed'))
        except Exception as exc:
            missing.append(f'{module}: {type(exc).__name__}: {exc}')
    model_dir = root / 'models' / 'sd15'
    model_ready = (model_dir / 'model_index.json').is_file()
    gpu = 'not available'
    try:
        import torch
        if torch.cuda.is_available():
            gpu = str(torch.cuda.get_device_name(0))
    except Exception:
        pass
    return {
        'ok': not missing,
        'frozen': bool(getattr(sys, 'frozen', False)),
        'python': sys.version.split()[0],
        'model_local': model_ready,
        'offline_ready': model_ready and not missing,
        'gpu': gpu,
        'versions': versions,
        'errors': missing,
        'note': 'Imports only; real image generation requires separate Windows acceptance test.',
    }
