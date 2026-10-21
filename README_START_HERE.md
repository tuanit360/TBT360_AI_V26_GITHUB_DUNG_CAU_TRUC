# TBT360 AI V81 – One-screen Studio / Import Dataset

This repository contains the V81 Gradio Studio application and its development/runtime support modules. Historical V66–V78 engines remain **only when used by active features or regression tests**; legacy V26 entry point and GUI are not part of the build.

## For Windows users without Python
Open the GitHub Actions artifact **TBT360_AI_V81_PORTABLE_WINDOWS_X64_CPU** after its Windows build passes. Extract the complete ZIP and run `TBT360_AI.exe`. Do not launch files inside the ZIP.

## Load images on one screen
At the top of the main Gradio page is **NẠP ẢNH HUẤN LUYỆN – IMPORT DATASET**.
1. Choose multiple JPG/PNG/WEBP images, or choose a ZIP archive.
2. Enter a project ID and a caption (draft label).
3. Press **LƯU ẢNH VÀ NHÃN NHÁP** or **NẠP ẢNH TỪ ZIP VÀO DATASET**.
4. View the gallery. The application automatically stores deduplicated images at `dataset/raw/<project_id>`.

Imported data is **not automatically used for training**. Labels must be reviewed and rights, project splits, and data quality assessed first. Current LoRA training requires CUDA with sufficient VRAM; CPU inference can be slow.

## Supplied architectural datasets
The user's ZIP/RAR uploads are not silently embedded in the executable or GitHub repository. They are sizeable and may contain SVG/DXF/JSON rather than photographic images. ZIP import currently accepts image formats only; RAR and vector-to-raster conversion are not supported here. A separately prepared 35-image review sample package is provided in the ChatGPT conversation, rather than being misrepresented as part of the GitHub EXE.

## Version validation
The visible app heading, CI workflow/job and downloadable artifact must all say **V81**. Running `--self-test` checks imports but not actual image generation; the workflow additionally tests the local Gradio HTTP launch. Full image-generation model weights are not included.
