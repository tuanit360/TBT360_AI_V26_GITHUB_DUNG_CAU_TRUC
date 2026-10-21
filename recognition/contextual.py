"""V78 contextual pixel learner. Trainable baseline with spatial context and validation-based selection.
Not a CNN, semantic detector, or verified image-to-BIM system.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
from recognition.learned import CATEGORIES, _image, load_manifest, scores


def _box_mean(a, radius):
    # Integral image: O(pixels), independent of window area.
    padded = np.pad(a, radius, mode='edge')
    integral = np.pad(padded.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    width = 2 * radius + 1
    return (integral[width:, width:] - integral[:-width, width:]
            - integral[width:, :-width] + integral[:-width, :-width]) / (width * width)


def contextual_features(image):
    a = image.astype(np.float64) / 255.0
    local = _box_mean(a, 2)
    broad = _box_mean(a, 6)
    horiz = np.abs(a - np.roll(a, 2, axis=1))
    vert = np.abs(a - np.roll(a, 2, axis=0))
    horiz[:, :2] = 0
    vert[:2] = 0
    return np.stack((np.ones_like(a), a, local, broad, a-local,
                     a-broad, horiz, vert), axis=-1).reshape(-1, 8).astype(np.float32)


def _predict(features, weights):
    return np.argmax(features @ weights, axis=1).astype(np.uint8)


def fit(dataset, checkpoint, report_path, epochs=100, patience=12, seed=17,
        learning_rate=0.3):
    if not isinstance(epochs, int) or not 1 <= epochs <= 500:
        raise ValueError('epochs must be 1..500')
    if not isinstance(patience, int) or not 1 <= patience <= epochs:
        raise ValueError('patience must be 1..epochs')
    if not 0 < learning_rate <= 1:
        raise ValueError('invalid learning rate')
    records, projects = load_manifest(dataset)
    by_split = {split: [] for split in ('train', 'validation', 'test')}
    for split, project, image, mask in records:
        by_split[split].append((project, contextual_features(image), mask.reshape(-1)))
    X = np.concatenate([x for _, x, _ in by_split['train']])
    y = np.concatenate([y for _, _, y in by_split['train']])
    rng = np.random.default_rng(seed)
    weights = rng.normal(0, .01, (X.shape[1], len(CATEGORIES))).astype(np.float32)
    counts = np.bincount(y, minlength=len(CATEGORIES)).astype(np.float64)
    class_weights = np.zeros_like(counts)
    present = counts > 0
    class_weights[present] = len(y) / (present.sum() * counts[present])
    sample_weights = class_weights[y]
    targets = np.eye(len(CATEGORIES), dtype=np.float32)[y]
    best_score = -1.0
    best_weights = weights.copy()
    best_epoch = 0
    stale = 0
    history = []
    for epoch in range(1, epochs + 1):
        logits = X @ weights
        logits -= logits.max(axis=1, keepdims=True)
        probs = np.exp(logits)
        probs /= probs.sum(axis=1, keepdims=True)
        grad = X.T @ ((probs - targets) * sample_weights[:, None]) / max(1.0, sample_weights.sum())
        weights -= learning_rate * grad.astype(np.float32)
        # Select only on validation; never inspect test during training/selection.
        vals = [scores(truth, _predict(feat, weights))['per_class'] for _, feat, truth in by_split['validation']]
        observed = []
        for cls in CATEGORIES[1:]:
            for metrics in vals:
                value = metrics[cls]['iou']
                if value is not None and metrics[cls]['support']:
                    observed.append(value)
        score = float(np.mean(observed)) if observed else 0.0
        history.append({'epoch': epoch, 'validation_foreground_iou': round(score, 6)})
        if score > best_score + 1e-6:
            best_score, best_weights, best_epoch, stale = score, weights.copy(), epoch, 0
        else:
            stale += 1
        if stale >= patience:
            break
    evaluation = {}
    for split, rows in by_split.items():
        truth = np.concatenate([m for _, _, m in rows])
        prediction = np.concatenate([_predict(x, best_weights) for _, x, _ in rows])
        evaluation[split] = scores(truth, prediction)
        evaluation[split]['per_project'] = {
            project: scores(mask, _predict(feat, best_weights))
            for project, feat, mask in rows
        }
    dest = Path(checkpoint)
    dest.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(dest, weights=best_weights, classes=np.array(CATEGORIES),
                        model_version=np.array('v78_contextual_v1'))
    report = {'model_type': 'v78_contextual_pixel_softmax', 'engineering_verified': False,
              'source': 'provided_annotated_dataset', 'splits': {k: sorted(v) for k, v in projects.items()},
              'selected_epoch': best_epoch, 'epochs_run': len(history),
              'validation_history': history, 'metrics': evaluation,
              'checkpoint_sha256': hashlib.sha256(dest.read_bytes()).hexdigest()}
    out = Path(report_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    return report


def infer(image_path, checkpoint, output):
    with np.load(checkpoint, allow_pickle=False) as state:
        if str(state['model_version']) != 'v78_contextual_v1':
            raise ValueError('Incompatible checkpoint version')
        weights = state['weights']
        if weights.shape != (8, len(CATEGORIES)) or list(state['classes']) != list(CATEGORIES):
            raise ValueError('Incompatible checkpoint dimensions/classes')
    image = _image(image_path)
    pred = _predict(contextual_features(image), weights).reshape(image.shape)
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(pred).save(destination)
    return {'output': str(destination), 'verification': 'unverified_pixel_prediction'}
