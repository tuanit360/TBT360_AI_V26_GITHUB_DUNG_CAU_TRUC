# V281: independent AI worker replacing Gradio-bound inference

The original Gradio UI and buttons are preserved, but image generation now
enters app.isolated_image_bridge.execute_image_job. It serializes a bounded
job to a local directory, starts a **different OS process**, and reads
validated PNG/ZIP/JSON only after the worker finishes. The worker imports
PyTorch/Diffusers itself and does not import Gradio or app.generate.

CPU-only PyTorch chooses CPU when RAM is sufficient. CUDA requires a separately
compatible environment. An inaccessible model, crash, timeout, or OOM cannot
be mislabeled as generated AI content; the existing V276 reference-only
fallback remains available. Worker console output is written to
logs/image_worker.log independently of Gradio.

The launcher reuses the same frozen executable with --worker-image and
run_portable.py dispatches this before app.generate.

Limits: This still uses Gradio for the UI and Diffusers for actual inference,
and its synchronous bridge awaits the worker. It does not guarantee zero
connection errors, surviving host-process OOM under all hardware pressure, or
successful CPU generation without weights. Real hardware acceptance is required.
