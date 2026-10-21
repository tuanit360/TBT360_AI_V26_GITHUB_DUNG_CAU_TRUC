# TBT360 AI V81 – Portable Windows x64

## Run V81 without installing Python
Extract the full V81 artifact `TBT360_AI_V81_PORTABLE_WINDOWS_X64_CPU.zip` into a new writable directory, such as `C:\\TBT360_AI_V81`. Do NOT launch from inside ZIP or copy the EXE alone.
Double-click `TBT360_AI.exe` (or `START_V81_DIAGNOSTIC.bat` for persistent error logs).
The Gradio Studio opens at http://127.0.0.1:7861/ (local only, share=False).
Do not reuse old V26/V78 folders to avoid mixing DLLs, data and scripts.

## One-screen training data intake
Use `NẠP ẢNH HUẤN LUYỆN – IMPORT DATASET` at the top of the screen to select multiple images or a ZIP of images; select/enter the project ID and draft caption, then press **LƯU ẢNH** or **NẠP ẢNH TỪ ZIP**. The built-in gallery shows the saved images.

To preload the user-supplied curated dataset, click the visible **NẠP BỘ DATASET V81 (GIỮ ĐÚNG TỪNG CÔNG TRÌNH)** button after choosing the separate `TBT360_AI_V81_ARCHITECTURAL_IMAGES_ALL_RASTER_PRELOADED.zip` in the ZIP selector. The app validates the pixel hashes and keeps the original seven image groups. Alternatively extract that data overlay into the EXE directory, preserving `dataset/raw/<project>/`. Click **XEM TẤT CẢ DATASET CÓ SẴN** to browse up to 80 images and see group counts. The 168 draft-labeled images are supplied separately in ChatGPT, not embedded in EXE / GitHub source because of size and provenance.
Each record is marked `NEEDS_REVIEW`; importing data does not train AI.

## Runtime and model limitations
- Windows x64 CPU build includes PyTorch CPU. NVIDIA CUDA is not available unless a separate compatible GPU build is supplied.
- Pretrained Stable Diffusion weights are NOT bundled. For true offline generation, provide a valid model in `models/sd15` before starting, with all required weights and config. Model files may be several GB.
- No training happened when importing images. True SD1.5 LoRA training requires reviewed split data and CUDA GPU.
- The `--self-test` probes package imports, not real image generation. CI additionally launches the UI and checks localhost readiness.

## Diagnostics
Run `START_V81_DIAGNOSTIC.bat` and send `logs/startup_console.log` / `logs/startup_error.log` on failure.
`manifest.json` and `SHA256SUMS.txt` allow verification of packaged file integrity.
