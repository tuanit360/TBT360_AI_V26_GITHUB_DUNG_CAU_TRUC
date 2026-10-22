"""Minimal reproducible image-to-BIM benchmark contracts.

A generated canonical BIM is *evaluated against* independent reference data.
No result is trained here; the score is not fabricated or inferred from
the architecture photograph.
"""
import math
from app.bim_transaction import validate_document


def score_bim_prediction(reference, prediction):
    validate_document(reference)
    validate_document(prediction)
    if reference['project_id'] != prediction['project_id']:
        raise ValueError('Evaluation must compare the same project')
    def by_id(doc):
        return {item['id']: item for item in doc['entities']}
    truth, found = by_id(reference), by_id(prediction)
    matched = set(truth) & set(found)
    correct_types = sum(truth[key]['category'] == found[key]['category'] for key in matched)
    precision = correct_types / len(found) if found else 0.0
    recall = correct_types / len(truth) if truth else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {'project_id': reference['project_id'], 'reference_entities': len(truth),
            'predicted_entities': len(found), 'matching_entity_ids': len(matched),
            'category_precision': round(precision, 6),
            'category_recall': round(recall, 6),
            'category_f1': round(f1, 6),
            'geometry_accuracy_evaluated': False,
            'reason': 'Concept geometry needs separate geometric ground-truth alignment',
            'reference_is_training_data': None}


def evaluation_gate(scores, minimum_projects=3):
    if not isinstance(scores, list) or len(scores) < minimum_projects:
        raise ValueError('Independent project holdout is too small')
    projects = {s.get('project_id') for s in scores}
    if len(projects) != len(scores):
        raise ValueError('Duplicate projects in independent evaluation')
    if any(s.get('reference_is_training_data') is not False for s in scores):
        raise ValueError('Holdout provenance must confirm disjoint training projects')
    mean = sum(s['category_f1'] for s in scores) / len(scores)
    return {'evaluated_projects': len(projects), 'mean_category_f1': round(mean, 6),
            'model_is_trained': False, 'geometry_verified': False,
            'meets_category_f1_0_8': mean >= 0.8}
