"""UI evidence readout uses the same LoRA validation as inference."""
from pathlib import Path
from app.lora_validation import validate_adapter


def training_evidence(root):
    folder = Path(root) / 'loras'
    runs = []
    if folder.is_dir():
        for directory in sorted(folder.iterdir()):
            if not directory.is_dir():
                continue
            result = validate_adapter(directory)
            runs.append({
                'name': directory.name,
                'checkpoint_verified': result['valid'],
                'status': 'CHECKPOINT_SHA256_VERIFIED' if result['valid'] else 'UNVERIFIED',
                'reason': result.get('reason', ''),
                'sha256': result.get('sha256'),
            })
    return {
        'verified': sum(record['checkpoint_verified'] for record in runs),
        'runs': runs, 'training_on_this_machine': False,
        'note': 'Checksum proves artifact integrity, not architecture model quality or provenance.',
    }
