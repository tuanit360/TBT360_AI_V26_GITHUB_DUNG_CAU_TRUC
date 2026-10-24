# V290 — worker diagnostic collection

When a child AI worker fails, the existing bridge produces
logs/last_failure_bundle.zip using a bounded privacy-redacted tail of
image_worker.log, generation_stage.log, runtime_errors.log, console and
fatal logs, plus the last worker state. Users can also run
BIMAI360.exe --last-failure-bundle without Gradio.

No images, prompt payloads, models, project files, or full environment
variables are intentionally included. Users must still review logs before
sharing; redaction is best-effort. This helps identify real worker faults
but does not claim any successful SD1.5 generation.
