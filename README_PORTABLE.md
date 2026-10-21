# TBT360 AI V65 — Portable Windows x64

Extract the complete TBT360_AI folder. Do NOT copy only the EXE.
No Python or pip installation is required on the target Windows PC.
Run CHECK_PORTABLE.bat first, then TBT360_AI.exe.
Web UI is local to 127.0.0.1:7861; do not expose this endpoint to the public Internet.
The folder `models/sd15` must contain valid model weights for truly offline image generation.
If the model is absent, first image generation will require Internet and the model may be several GB.
GPU build requires a supported NVIDIA driver. CPU build is widely compatible but very slow.
The runtime self-test does not replace testing one real image generation.
manifest.json and SHA256SUMS.txt list shipped files and integrity hashes.
