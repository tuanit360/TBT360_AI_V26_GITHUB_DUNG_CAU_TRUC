# TBT360 AI V69 — Learning / BIM evidence gate

## Exactly what is new
- Human feedback is opt-in, append-only `feedback/review_queue.jsonl`, pending review. **Not** an automatic model weight update. Feedback must be curated, licensed and assessed before manual LoRA retraining.
- Grouped train/validation split by `project_id` with deterministic SHA256 ordering and exact duplicate-file screening. V69 blocks LoRA training unless a `project_manifest.jsonl` exists and `metadata.jsonl` contains *train images only*. Minimum three projects and five train images.
- Bounded canonical BIM geometry validation (meters, entity IDs, bbox dimensions, door/window host containment), and geometry comparison by ID. It **does not** interpret a picture as dimensional BIM or verify engineering code.
- Checkpoint selection using supplied *measured* train/holdout validation scores (normalized 0–1), an overfit gap threshold and reproducible seed/input eligibility checks. It **does not** compute these metrics from model inference itself.
- Separate Gradio feedback and BIM upload tab. Remains on SD1.5 for LoRA trainer; SDXL/ControlNet/upscale are optional inference pathways from V68.

## Real dataset contract (required for actual training)
Put licensed architecture images into `dataset/prepared`. Create `project_manifest.jsonl` with one entry per image:

```json
{"project_id":"OFFICE_A01","file_name":"office_a_01.png","caption":"front perspective of building A01, 2 floors, glazing...","discipline":"architecture","verification":"concept"}
```

Use at least three different projects. Captions must match observed content; `verification` must be one of `concept`, `geometry_validated`, `engineering_verified`, and must not claim engineering verification without evidence. Cross-project near-duplicates still need human review.

Run `python -m tools.prepare_grouped_dataset --prepared dataset/prepared` to generate training-only `metadata.jsonl` (the previous metadata, if any, is backed up). The validation images **stay outside training metadata** and must be evaluated separately on the GPU using fixed inputs and seeds. `python -m training.run_lora` then checks the gate again before creating training output. This does **not** make the Hugging Face LoRA trainer perform periodic validation; extra evaluation is required.

### Audit / geometry / checkpoint commands
```
python -m tools.learning_workflow audit --manifest dataset/prepared/project_manifest.jsonl --root dataset/prepared --out dataset/project_split_audit.json
python -m tools.learning_workflow bim --input demo_data/canonical_office_example.json
python -m tools.learning_workflow checkpoints --input demo_data/checkpoints_example.json
python -m unittest discover -s tests -v
```

`demo_data` uses **synthetic program-authored geometry and illustrative numerical scores** solely to test code branches. It is not real photographed architecture, model training, proof of model quality or proof of learned BIM.

## Quality acceptance to run on Windows GPU with real licensed data
1. Validate license/provenance and labels manually, then run split audit and resolve any duplicate/leak flags.
2. Retain fixed, genuinely unseen building project(s) with real ground truth, never use them to update LoRA.
3. Train multiple actual checkpoints with the same base model and data split. Save trainer logs, true weights hashes, validation scores and seed/input lists.
4. Generate matched before/after images for identical input/seed/prompt/control and measure perceptual, geometric and domain review. Pixel appearance is not evidence of real dimension consistency.
5. Select checkpoint by held-out score, reject overfit/invalid measurements, manually approve release. Never automatically train from unreviewed feedback.
6. For real BIM comprehension implement an image-to-geometry/CAD recognition pipeline with human annotation and robust spatial verification; this release does **not** provide it.

## Boundaries
This Linux environment does not compile/test a Windows EXE or run actual CUDA LoRA training. There is no user-provided licensed labeled photo dataset here; no real-image training, GPU benchmarks or claims of BIM competence are made. The model and optional checkpoint weights must still be downloaded on the Windows build machine.
