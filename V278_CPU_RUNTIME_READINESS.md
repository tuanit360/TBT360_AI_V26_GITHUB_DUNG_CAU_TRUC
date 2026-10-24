# BIMAI360 V278 — CPU runtime readiness

A reference image displayed by the V276 fallback is not an AI image. V278
adds an explicit runtime preflight inside the existing generation callback
before any Diffusers pipeline is loaded. CPU-only PyTorch is a supported
execution mode if at least 7 GiB RAM is available, model files are valid
and the machine can complete inference. Insufficient RAM returns an actionable
failure, retaining the original source-image display.

This patch does NOT make CPU inference faster, bundle missing SD1.5 weights,
fix driver failures, guarantee crash-proof Gradio or make fake AI images.
Use the existing CPU portable launcher for CPU-only operation; CUDA VENV is
separate. No buttons or layout have changed.

Production acceptance still requires Windows CI, extracted ZIP smoke and a
genuine CPU generation test with a valid model.
