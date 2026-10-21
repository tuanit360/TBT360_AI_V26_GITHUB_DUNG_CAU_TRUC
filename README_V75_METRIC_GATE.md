# V75 — BIM metric geometry evidence gate

This version adds `evaluation/metric_gate.py`, comparing explicitly supplied BIM bounding boxes and host relationships with separately supplied metric annotation JSON. It rejects modified input (SHA256), holdout/train overlap, missing projects, missing/extra entity IDs, class mismatch, invalid geometry or host-reference mismatch. Reports absolute coordinate errors in **metres**, per project and class, then applies a configurable tolerance.

## Quick offline demonstration

`python -m evaluation.metric_gate demo_data/v75_metric/manifest.json --assets demo_data/v75_metric --output reports/v75_metric_demo.json --tolerance-m 0.02`

Or `DANH_GIA_KICH_THUOC_V75_WINDOWS.bat` with Python on the build PC.

**Source of demo data:** deterministic synthetic two-office fixtures from authored V74 BIM JSON; annotation geometry is deliberately altered by 0.01m to exercise the checks. Not real-world measured buildings, not AI inference, not engineering certification. These fixtures must never be used to claim model quality.

## For independent evaluation

Prepare verified model output for each building as `predicted_bim`, and a separate independently produced ground-truth geometry as `independent_annotation`. Give both the same stable entity IDs, type and `bbox_m` coordinates in metres. List each holdout building once and include its SHA256. Never train on those buildings.

This stage does **not** estimate geometry from images, produce automatic BIM from drawings, retrain LoRA, or approve checkpoints. It is a quantitative evidence gate that can accompany V73 paired image/seed evaluation. Review both reports before any checkpoint promotion.

For portable Windows builds use the existing BUILD_CPU_WINDOWS_X64.bat / BUILD_NVIDIA_WINDOWS_X64.bat scripts on a Windows x64 machine with Python. Windows EXE and AI weights are not included.
