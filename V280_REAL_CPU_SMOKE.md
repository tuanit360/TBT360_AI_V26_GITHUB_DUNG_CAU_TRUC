# V280: actual CPU SD1.5 image-to-image smoke

No new engine or replacement UI. Extends the existing
tools/smoke_real_image_inference.py to accept --device cpu|cuda|auto and
adds START_V280_CPU_REAL_IMAGE_TEST.bat for an isolated CPU-only proof.
Use Python 3.11 VENV with dependencies and a legitimate full SD1.5
Diffusers checkpoint at models/sd15. Run from the extracted repository.

Success requires real inference, a reopened valid PNG and a SHA256 report
under output/v280_cpu_real_smoke. Missing/incomplete model or insufficient
available RAM fails with a nonzero exit code and a local log. CI only checks
the CLI contract/negative cases because the runner does not carry SD1.5
weights; do not claim real inference PASS from Windows CI alone.

Existing user interface, buttons and AI/BIM persistence are unchanged.
