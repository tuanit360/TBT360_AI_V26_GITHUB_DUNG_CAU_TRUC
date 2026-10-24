"""Evaluate architecture VLM predictions against held-out, labelled projects.

This module scores real supplied predictions; it never creates model outputs.
Splits are project-disjoint to prevent multi-view image leakage.
"""
from collections import Counter
from app.architecture_evidence import FIELDS


def evaluate_predictions(records):
    if not isinstance(records, list) or not records:
        raise ValueError('Labelled independent evaluation records required')
    projects, per_field = set(), {field: Counter() for field in FIELDS}
    for record in records:
        if not isinstance(record, dict) or set(record) != {
            'project_id', 'split', 'truth', 'prediction', 'inference_completed'
        }:
            raise ValueError('Invalid evaluation record')
        project = record['project_id']
        if not isinstance(project, str) or not project:
            raise ValueError('Missing project identifier')
        if project in projects:
            raise ValueError('Only one held-out aggregate per project is allowed')
        projects.add(project)
        if record['split'] != 'test' or record['inference_completed'] is not True:
            raise ValueError('Only actual inference on independent test projects counts')
        truth, predicted = record['truth'], record['prediction']
        if not isinstance(truth, dict) or not isinstance(predicted, dict):
            raise ValueError('Expected labelled values')
        if set(truth) != set(FIELDS) or set(predicted) != set(FIELDS):
            raise ValueError('Missing a labelled architecture attribute')
        for field in FIELDS:
            actual, guess = truth[field], predicted[field]
            if actual is None:
                continue
            metric = per_field[field]
            metric['labelled'] += 1
            if guess is None:
                metric['abstained'] += 1
            elif str(guess).strip().casefold() == str(actual).strip().casefold():
                metric['correct'] += 1
            else:
                metric['incorrect'] += 1
    metrics = {}
    for field, data in per_field.items():
        labelled = data['labelled']
        metrics[field] = {
            'labelled': labelled,
            'correct': data['correct'],
            'incorrect': data['incorrect'],
            'abstained': data['abstained'],
            'coverage': round((labelled-data['abstained'])/labelled, 6) if labelled else None,
            'accuracy_including_abstention': round(data['correct']/labelled, 6) if labelled else None,
        }
    return {'schema': 'bimai360.vlm_holdout_metrics.v201',
            'evaluated_projects': len(projects), 'metrics': metrics,
            'architecture_model_trained_here': False,
            'metric_geometry_accuracy_evaluated': False,
            'ifc_validated': False}
