from __future__ import annotations
import argparse
import json
from pathlib import Path
from learning.project_evidence import evaluate_project_bundle, evaluate_checkpoint_trials, draft_promotion
from learning.core import write_json


def main():
    parser = argparse.ArgumentParser(description='TBT360 V70 offline architecture/BIM evidence gates')
    sub = parser.add_subparsers(dest='command', required=True)
    bundle = sub.add_parser('bundle')
    bundle.add_argument('--manifest', type=Path, required=True)
    bundle.add_argument('--root', type=Path, required=True)
    bundle.add_argument('--out', type=Path)
    trials = sub.add_parser('trials')
    trials.add_argument('--input', type=Path, required=True)
    trials.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.command == 'bundle':
        result = evaluate_project_bundle(args.manifest, args.root)
    else:
        result = evaluate_checkpoint_trials(json.loads(args.input.read_text(encoding='utf-8')))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if args.out:
        write_json(args.out, result)
    if result['status'] == 'BLOCKED':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
