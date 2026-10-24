# V276 — display fallback without CUDA

The current Gradio layout, all existing commands and image generation behavior
remain unchanged. On **AI generation failure only**, the existing output HTML
now shows an inline bounded PNG preview of the **uploaded source image**,
clearly marked "KHÔNG PHẢI ẢNH AI". The failure reason and diagnostic transcript
are preserved exactly; the ZIP result remains empty. A successful AI result
continues to be displayed unchanged.

This no-CUDA fallback uses Pillow and an embedded PNG data URI rather than the
Gradio file endpoint. It does not synthesize a new design, turn a source into
an AI-generated image or bypass missing/invalid model checks.

For actual CPU AI inference, launch the already-present
CHAY_BIMAI360_CPU_KHONG_CUDA.bat and ensure sufficient free RAM and valid
SD1.5 weights. Actual GPU/CPU model inference remains hardware-dependent.

Required verification: regression, Windows frozen Gradio callback smoke,
extracted ZIP integrity, and a real user-machine trial. No production readiness
claim until those gates pass.
