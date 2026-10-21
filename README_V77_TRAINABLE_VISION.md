# V77 – Trainable Vision Baseline (Python/NumPy)

This update adds **genuine fitted weights** via a small pixel-wise softmax classifier for class IDs background, wall, door, window and column. It is deliberately a **baseline**, not an architectural object detector, transformer, segmentation foundation model, or reliable image-to-BIM implementation. Simple 3×3 pixel features have no spatial reasoning and cannot infer metric dimensions, relationships or floors. V76 deterministic recognition remains.

## Dataset contract

`manifest.json` requires samples with `project_id`, `split` (train/validation/test), `image`, `mask`, `image_sha256`, `label_status: annotated`, `usage_allowed: true`. PNG masks must be single-channel class IDs 0–4 with image-sized dimensions. Splits must not share projects. Real datasets should also be checked for near duplicates, provenance, licenses and independent engineering QA using the V71+ gates.

Run Windows: `TRAIN_VISION_V77_WINDOWS.bat` to train on **synthetic test-only data**; or use `python -m tools.train_vision_v77 --dataset MY_DATASET --checkpoint output/my_model.npz --report output/my_metrics.json`. Checkpoints are NumPy arrays, no GPU necessary. Reports include train/validation/test per-class IoU, precision, recall, support and accuracy. Scores from tiny synthetic examples have no claim of generalization.

Dependencies: `numpy`, `Pillow` already in the project's requirements. No new heavyweight dependencies. Windows EXE/Portable build has not been verified. No real building images, production checkpoint or AI quality claim is shipped.
