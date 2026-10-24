"""Choose the newest validated local LoRA checkpoint for Windows inference."""
from __future__ import annotations

import argparse
from pathlib import Path

from app.lora_validation import validate_adapter


def newest_verified_adapter(root: Path) -> str:
    root = Path(root)
    if not root.is_dir():
        raise ValueError('No LoRA checkpoint directory')
    candidates = []
    for folder in root.iterdir():
        if not folder.is_dir() or folder.is_symlink():
            continue
        result = validate_adapter(folder)
        if result.get('valid'):
            candidates.append((folder.stat().st_mtime_ns, folder.name))
    if not candidates:
        raise ValueError('No verified LoRA checkpoint available')
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
