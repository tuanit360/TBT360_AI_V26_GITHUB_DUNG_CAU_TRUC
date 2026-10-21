# TBT360 AI V72 – Certified project holdout training

V72 fixes a substantive limitation: the old one-click training script did not enforce the V71 approved manifest. `TRAIN_LORA_WINDOWS.bat` now **blocks** unless a V71 manifest passes all provenance, image integrity, deduplication and project-split checks. A certified staging job exports **only train images** to the folder consumed by Diffusers. Validation is physically isolated.

## Windows build machine workflow

1. Provide licensed real architecture images in `dataset/raw`, and a manifest at `dataset/manifest_v71.jsonl` with per-image project IDs, captions, SHA256, rights and `consent_to_train`.
2. Install required dependencies on the **build** machine (existing setup). Run `CHUAN_BI_V72_WINDOWS.bat`. It creates `dataset/v72_certified` once, with train and validation in separate subfolders and a certificate of image + metadata hashes. Never replace an approved dataset folder in place.
3. Run `TRAIN_LORA_WINDOWS.bat` on an NVIDIA GPU machine with enough VRAM; it verifies certificate and uses only train images.
4. Holdout validation must be evaluated separately with fixed prompts, seeds, input geometry and verified BIM labels. Do not call a checkpoint approved without independent quality evidence, even if its weights were produced successfully.

## What changed and what is not proven

- Training now uses project-isolated train images, not the legacy unreviewed prepared folder.
- Validation image bytes and caption metadata have checksums; any tampering blocks the trainer.
- Existing checkpoint and BIM review tools remain available from V70/V71.
- SHA256 checks provide integrity, *not* label truth, model quality or copyright validation.
- V72 **does not automatically re-train after a user's feedback**, does not magically learn BIM semantics from images, and does not yet perform GPU-based architecture fidelity evaluation. Existing synthetic tests only verify program logic.
- No trained weights, local AI models or real Windows `.exe` are included in this small source ZIP.
