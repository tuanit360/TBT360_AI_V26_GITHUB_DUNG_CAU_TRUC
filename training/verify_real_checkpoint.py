"""Verify completed LoRA training using the shared strict checkpoint validator."""
import argparse
import json
from pathlib import Path

from app.lora_validation import validate_adapter


def verify_checkpoint(path):
    folder = Path(path)
    status_path = folder / 'training_status.json'
    status = json.loads(status_path.read_text(encoding='utf-8'))
    if status.get('status') != 'SUCCEEDED':
        raise ValueError('Training did not complete successfully')
    steps = status.get('steps')
    if type(steps) is not int or steps < 50:
        raise ValueError('Training has fewer than 50 verified steps')
    result = validate_adapter(folder)
    if not result['valid']:
        raise ValueError('Invalid LoRA checkpoint: ' + result['reason'])
    if type(status.get('tensor_count')) is not int:
        raise ValueError('Missing checkpoint tensor count')
    return {
        'verified_checkpoint': True,
        'weights_sha256': result['sha256'],
        'tensor_count': result['tensor_count'],
        'model_type': 'SD1.5 LoRA',
        'trained_vlm': False,
        'image_to_bim_model': False,
        'accuracy_evaluated': False,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', required=True)
    arguments = parser.parse_args()
    print(json.dumps(verify_checkpoint(arguments.path), indent=2))
