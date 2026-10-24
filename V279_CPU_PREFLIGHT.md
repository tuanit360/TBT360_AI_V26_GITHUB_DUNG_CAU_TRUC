# V279 CPU image-generation preflight

This release adds `BIMAI360.exe --cpu-preflight` and
`python run_portable.py --cpu-preflight` as non-Gradio diagnostic modes.

It checks CPU PyTorch, current physical RAM and complete offline model assets,
then writes `logs/cpu_preflight.json`. It never loads Diffusers, downloads a
model, changes Gradio UI, or claims that an image was generated.

Use `CHAY_BIMAI360_CPU_KHONG_CUDA.bat` for the actual CPU app.
If the preflight is ready but generation still fails, inspect
`logs/generation_stage.log` and `logs/runtime_errors.log`.
An online model download remains a dependency and is not guaranteed.

A true end-to-end test with a fully downloaded SD1.5 model is still needed
on customer CPU hardware. Do not treat this preflight as that test.
