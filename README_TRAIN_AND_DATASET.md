# BIMAI360: dataset intake, GPU training and release gates (V211)

## User-provided files
Do not commit private architecture RAR files to a public GitHub repository.
Copy files under an access-controlled workspace where the authorized GPU
runner can read them. Do not assume images alone contain ground-truth BIM.

Use `python -m training.audit_uploaded_archives --output archive_audit.json "source/first.rar" "source/second.rar"`.
RAR scanning requires the Python `rarfile` package and an available unrar/
bsdtar/unar backend. When missing, the audit explicitly FAILS instead of
pretending to parse archives. This inventory counts files and extensions,
not architectural correctness or project alignment.

Before training, create project-level labels and explicit linkages:
project_id, role (front exterior / floorplan / elevation / section / interior /
MEP / 3D), source_image_hash, canonical_bim_uri, units, measured geometry,
verification status, license and user approval. Split by PROJECT, not by image.

## GPU and automatic training
Run `python -m training.hardware_preflight` on the exact GPU runner.
The photographed user's machine has 16 GB RAM and NVIDIA T600 Laptop GPU;
the screenshot does not show its VRAM. Current SD1.5 LoRA workflow requires
at least 8 GiB VRAM to proceed; do not promise local training before
checking GPU RAM. Training is explicitly triggered on an authorized Linux
self-hosted CUDA runner labelled `bimai360-gpu`, with dependencies installed,
certified dataset staged privately, and accepted model access/licenses.
Workflow: `.github/workflows/gpu-train.yml`.

The existing GPU workflow trains image-generation SD1.5 LoRA, NOT a multimodal
architecture-to-BIM model. Do NOT treat a generated SD1.5 LoRA as a
trained vision-language model. The Windows CPU Portable runs without it.

## Product-ready gates
1. A separate real VLM checkpoint is installed and completes inference.
2. Provenance includes checkpoint digest, model/processor metadata and image hash.
3. At least 3 whole unseen projects have paired verified CAD/BIM ground truth.
4. Schema and cross-view geometry checks run, plus Save/Reopen and GLB/DXF roundtrip.
5. CI Windows exe starts, regression succeeds, and artifact integrity passes.
6. CPU/VRAM/time benchmark is reported; never count generated placeholder
   plans, IFC files, or technical MEP as verified design.
7. Release one cumulative ZIP with sample project, API schema and evidence.

Current state: training code/workflows exist, but no GPU runner connection,
trained architecture VLM, trained photo-to-full-BIM checkpoint or executed
training evidence is available from this code change alone.
