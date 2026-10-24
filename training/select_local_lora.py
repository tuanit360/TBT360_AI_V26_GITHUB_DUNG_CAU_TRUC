"""Select the newest usable SD1.5 LoRA, not merely a readable tensor file."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from training.verify_real_checkpoint import verify_checkpoint

EXPECTED_BASE_MODEL = 'stable-diffusion-v1-5/stable-diffusion-v1-5'


def newest_verified_adapter(root: Path) -> str:
    root = Path(root)
    if not root.is_dir():
        raise ValueError('No LoRA checkpoint directory')
    candidates = []
    for folder in root.iterdir():
        if not folder.is_dir() or folder.is_symlink():
            continue
        try:
            status = json.loads(
                (folder / 'training_status.json').read_text(encoding='utf-8'),
            )
            if not isinstance(status, dict):
                continue
            if status.get('base_model') != EXPECTED_BASE_MODEL:
                continue
            verify_checkpoint(folder)
            candidates.append((folder.stat().st_mtime_ns, folder.name))
        except (OSError, ValueError, TypeError, RuntimeError):
            continue
    if not candidates:
        raise ValueError('No verified SD1.5 LoRA checkpoint available')
    return max(candidates)[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('loras'))
    args = parser.parse_args()
    try:
        name = newest_verified_adapter(args.root)
    except (OSError, ValueError) as exc:
        parser.exit(2, f'BIMAI360: {exc}\n')
    print(name)


if __name__ == '__main__':
    main()
