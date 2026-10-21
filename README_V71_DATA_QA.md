# TBT360 AI V71 — Dataset Quality & Leakage Gate

This is an **incremental update to V70**, not a trained new model. It adds a fail-closed audit for decoded PNG/JPG/WebP image files before assembling training examples. Files without a positive `consent_to_train`, source and license statements are rejected (these fields are self-declared; the tool cannot legally verify a license).

## Workflow on a build machine (Python 3.11)

1. Put **real, licensed images** under `dataset/raw`; do not reuse the synthetic test fixtures as training data.
2. Create `dataset/manifest_v71.jsonl` with one JSON object per image, for example:

```json
{"project_id":"OFFICE_001","file_name":"OFFICE_001/front.png","sha256":"<ACTUAL_SHA256>","caption":"Office exterior, glazed facade and visible entrance","discipline":"architecture","verification":"concept","label_classes":["facade","window","door"],"license":"licensed-by-owner","source":"original photo by owner","consent_to_train":true}
```

3. Run `python -m learning.data_quality --manifest dataset/manifest_v71.jsonl --root dataset/raw --out dataset/quality_v71.json` or `AUDIT_DATASET_V71_WINDOWS.bat` after setting up the Python build environment.
4. **Do not begin training if the audit is BLOCKED.** Only use `train_files` to train, and keep `validation_files` excluded from training. Do not claim this audit can verify that labels, dimensions, camera positions, BIM mappings, or image rights are factual.

The old `TRAIN_LORA_WINDOWS.bat` remains for backward compatibility. It does **not** automatically run this V71 audit, and it does not guarantee held-out validation. A production operator must enforce the new gate before using that older training script; integrating project-preserving splits into the trainer remains future work.

## What is actually validated

- Source-file SHA256, decodeability and minimum 256×256 resolution.
- Required project ID, discipline, label classes, caption, verification status, recorded license and explicit training consent.
- Exact duplicates and dHash near duplicates across different projects, including potential train-validation contamination.
- Deterministic project-wise train/validation split, exporting file lists **only on PASS**.
- Path traversal attempts are blocked.

dHash flags potential duplicates for review; it may yield false positives and can miss crops or transformations. The V71 audit is intentionally conservative. It is not a trained visual classifier. The checkpoint gate, BIM JSON checker, ControlNet and SDXL paths from V70 remain unchanged.

## Verification status

Tests use **synthetic fixture images**, not real architectural training/evaluation images. Windows EXE and GPU training/inference are **not tested in this environment**. No actual model quality or smoothness improvement can be claimed until measured on real independent projects.
