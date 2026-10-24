# BIMAI360 V273 — offline diagnostic recovery

This change builds on the already-passing V271 LoRA fix without replacing it.

When Gradio callbacks all fail, including the LOG button, run
`START_BIMAI360_DIAGNOSTIC.bat` from an extracted writable directory,
then run `EXPORT_DIAGNOSTICS_OFFLINE_WINDOWS.bat` to collect diagnostics
without depending on Gradio. Inspect logs before sharing them.

Changes:
- Capture startup_console.log in the redacted diagnostics ZIP.
- Use an offline diagnostics launcher with embedded Python fallback.
- Publish generated-image archives via a temporary ZIP, content hashes and atomic replace.
- Add regression tests for the offline diagnostic path and atomic export.

Not established: the underlying Windows disconnect cause, native OOM isolation,
Windows EXE startup, real GPU inference or end-to-end Gradio callback recovery.
