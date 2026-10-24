"""Replay VLM holdout evaluations from auditable on-disk predictions.

Requires actual recorded inference outputs and independent ground-truth labels.
Never substitutes training-set labels for held-out measurements.
"""
import argparse
import json
from pathlib import Path
from evaluation.vlm_architecture_holdout import evaluate_predictions


def evaluate_jsonl(path):
    source = Path(path)
    if not source.is_file() or source.stat().st_size > 20_000_000:
        raise ValueError('Holdout evaluation JSONL is missing or too large')
    records = []
    for index, line in enumerate(source.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        if len(line) > 100_000:
            raise ValueError('Oversized holdout record')
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f'Invalid JSONL record at line {index}') from exc
    report = evaluate_predictions(records)
    report['report_kind'] = 'actual_recorded_model_predictions'
    report['training_performed_during_evaluation'] = False
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    report = evaluate_jsonl(args.input)
    Path(args.output).write_text(json.dumps(report, indent=2), encoding='utf-8')
