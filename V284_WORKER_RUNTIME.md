# V284 — diagnose actual frozen inference dependencies

The new `BIMAI360.exe --worker-runtime-self-test` starts the same frozen EXE
in a separate child process. The child imports the packaged torch and
Diffusers libraries, inspects CPU/CUDA capability, and reports whether
the local checkpoint is complete. It writes `logs/worker_runtime_v284.json`.

This distinguishes worker transport PASS from usable inference dependencies.
Model missing is a reported issue, not a fake CI failure (CI has no model).
The test never claims an AI image was generated. Running a real SD1.5 job
and validating its PNG/ZIP remains mandatory for inference acceptance.

No Gradio UI, command registry, BIM schema, or image prompt is changed.
