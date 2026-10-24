"""Local VLM checkpoint preflight without downloading, loading or trusting code.

A config is evidence of model structure, not proof of accuracy, training,
or successful generation. Actual inference is separately required.
"""
import hashlib
import json
from pathlib import Path

MAX_CONFIG_BYTES = 1024 * 1024
ALLOWED_WEIGHTS = ('model.safetensors', 'model.safetensors.index.json')


def inspect_local_vlm_checkpoint(folder):
    base = Path(folder).expanduser().resolve()
    config_path = base / 'config.json'
    if not base.is_dir() or not config_path.is_file():
        raise ValueError('Missing local VLM config.json')
    if config_path.stat().st_size > MAX_CONFIG_BYTES:
        raise ValueError('Checkpoint config too large')
    try:
        config = json.loads(config_path.read_text(encoding='utf-8'))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('Invalid checkpoint configuration') from exc
    if not isinstance(config, dict) or not isinstance(config.get('model_type'), str):
        raise ValueError('Checkpoint must identify a concrete model type')
    if not (base / 'preprocessor_config.json').is_file() and not (
            base / 'processor_config.json').is_file():
        raise ValueError('Missing image processor configuration')
    weights = [base / name for name in ALLOWED_WEIGHTS if (base / name).is_file()]
    if not weights:
        raise ValueError('Checkpoint must include safetensors weights or sharded index')
    found = []
    index = base / 'model.safetensors.index.json'
    if index.is_file():
        if index.stat().st_size > MAX_CONFIG_BYTES * 8:
            raise ValueError('Weights index too large')
        mapping = json.loads(index.read_text(encoding='utf-8')).get('weight_map')
        if not isinstance(mapping, dict) or not mapping:
            raise ValueError('Empty or invalid weights map')
        shards = set(mapping.values())
        if any(not isinstance(name, str) or Path(name).name != name or
               not name.endswith('.safetensors') for name in shards):
            raise ValueError('Invalid checkpoint shard filename')
        found = [base / name for name in sorted(shards)]
    else:
        found = [base / 'model.safetensors']
    for weight in found:
        if not weight.is_file() or weight.is_symlink() or weight.stat().st_size <= 1024:
            raise ValueError('Missing, symlinked or incomplete safetensors shard')
    return {'checkpoint_type': config['model_type'],
            'checkpoint_directory': base.name,
            'weights_files': [x.name for x in found],
            'checkpoint_files_present': True,
            'model_loaded': False,
            'architecture_finetune_verified': False,
            'image_to_bim_trained': False,
            'gpu_inference_verified': False}
