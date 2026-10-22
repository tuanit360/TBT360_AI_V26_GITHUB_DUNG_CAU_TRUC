"""Verify that an actual trainer produced valid LoRA tensor weights."""
import argparse
import hashlib
import json
from pathlib import Path


def verify_checkpoint(path):
    folder = Path(path)
    status_path = folder / 'training_status.json'
    weights = folder / 'pytorch_lora_weights.safetensors'
    if not status_path.is_file() or not weights.is_file():
        raise ValueError('Missing training status or tensor weights')
    status = json.loads(status_path.read_text(encoding='utf-8'))
    if status.get('status') != 'SUCCEEDED' or status.get('steps', 0) < 50:
        raise ValueError('Training did not complete successfully')
    digest = hashlib.sha256(weights.read_bytes()).hexdigest()
    if digest != status.get('weights_sha256'):
        raise ValueError('Checkpoint SHA256 mismatch')
    try:
        from safetensors import safe_open
    except ImportError as exc:
        raise RuntimeError('Install safetensors to inspect real tensor weights') from exc
    with safe_open(str(weights), framework='pt', device='cpu') as file:
        keys = list(file.keys())
        if not keys:
            raise ValueError('No learned tensors')
        if len(keys) != status.get('tensor_count'):
            raise ValueError('Tensor count does not match trainer result')
        for key in keys:
            shape = file.get_slice(key).get_shape()
            if not shape or any(d <= 0 for d in shape):
                raise ValueError('Invalid tensor dimension')
    return {'verified_checkpoint': True, 'weights_sha256': digest,
            'tensor_count': len(keys), 'model_type': 'SD1.5 LoRA',
            'trained_vlm': False, 'image_to_bim_model': False,
            'accuracy_evaluated': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', required=True)
    arguments = parser.parse_args()
    print(json.dumps(verify_checkpoint(arguments.path), indent=2))
