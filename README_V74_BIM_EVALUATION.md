# TBT360 AI V74 — BIM plan evidence

Adds strict canonical BIM JSON validation and **2D plan** rasterization of axis-aligned bounding boxes, with per-class IoU against independent human annotations (`wall_annotated.png`, `door_annotated.png`, `window_annotated.png`). Each annotation is a binary grayscale image aligned to the exact bounds and dimensions. Missing evidence fails closed.

Run `DANH_GIA_BIM_V74_WINDOWS.bat` after creating annotations, or use `python -m evaluation.bim_plan demo_data/canonical_office_example.json --annotations dataset/v74_annotations --bounds 0 0 10 8 --width 1024 --height 768 --classes wall door window --output reports/v74_bim_plan.json`.

Important: no 3D perspective rendering, no automatic camera matching, no annotation inferred from the same model, no automatic training or checkpoint promotion. This is **deterministic geometry software QA**, not an AI BIM understanding benchmark. The test data is synthetic; no real building photo or third-party training data is bundled. V73 paired image evaluation remains a separate step. Checkpoints and Windows executable are not included.
