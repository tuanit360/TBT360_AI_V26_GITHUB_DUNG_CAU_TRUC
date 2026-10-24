# BIMAI360 V277 — local inference stage breadcrumbs

When Gradio remains at 0% or returns Connection errored out, the previous
UI callback cannot reveal whether inference, PNG encoding, ZIP export or
model loading was reached. Generation now appends a small bounded log to
logs/generation_stage.log without using Gradio, CUDA, torch or network access.
The offline diagnostic ZIP includes this log.

Look for the most recent BEGIN without matching DONE:
- MODEL_LOAD: loading CPU/GPU model.
- INFERENCE: running Diffusers model; 0% alone does not prove the image exists.
- PNG_SAVE: writing the verified PNG.
- ZIP_EXPORT: publishing ZIP.
- FAILED: Python exception was caught.

If logs stop abruptly without FAILED, inspect startup_console.log,
python_fatal.log and Windows Event Viewer; native OOM or process termination
may prevent Python exception handlers from running.

This change does not claim to fix a process crash or synthesize an AI image.
UI layout, command buttons and generated-image quality checks remain intact.
