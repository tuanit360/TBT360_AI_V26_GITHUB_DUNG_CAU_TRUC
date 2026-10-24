"""Prepare train-only LoRA metadata after project and image-leakage audit."""
import argparse
import json
from pathlib import Path

from learning.core import write_json
from tools.training_leakage_check import check_training_leakage
from learning.core import dataset_audit


def prepare(prepared: Path):
    folder = Path(prepared).resolve()
    manifest = folder / 'project_manifest.jsonl'
    audit = dataset_audit(manifest, folder)
    write_json(folder.parent / 'project_split_audit.json', audit)
    leakage = check_training_leakage(manifest, folder)
    write_json(folder.parent / 'training_leakage_audit.json', leakage)
    if audit['status'] != 'PASS' or leakage['status'] != 'SPLIT_VALID_NOT_TRAINED':
        raise ValueError('BLOCKED: review project_split_audit.json and training_leakage_audit.json')
    target = folder / 'metadata.jsonl'
    if target.exists():
        raise FileExistsError(
            'metadata.jsonl already exists: review and move it manually before regeneration'
        )
    # Write atomically; partial metadata must never become a trainable dataset.
    temporary = folder / 'metadata.jsonl.tmp'
    if temporary.exists():
        raise FileExistsError('Stale metadata.jsonl.tmp: inspect before retrying')
    try:
        with temporary.open('x', encoding='utf-8') as output:
            for row in audit['records']['train']:
                output.write(json.dumps({
                    'file_name': row['file_name'],
                    'text': row['caption'],
                }, ensure_ascii=False) + '\n')
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return audit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepared', type=Path, default=Path('dataset/prepared'))
    args = parser.parse_args()
    result = prepare(args.prepared)
    print(
        f'TRAIN projects: {result["train_projects"]}; '
        f'VALIDATION projects: {result["validation_projects"]}'
    )


if __name__ == '__main__':
    main()
