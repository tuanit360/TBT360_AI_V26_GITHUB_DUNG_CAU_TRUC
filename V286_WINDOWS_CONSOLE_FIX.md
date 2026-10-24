# V286 — Windows frozen worker console encoding

V285 CI failed **after** all regression tests passed. The packaged EXE
printed Vietnamese JSON through the runner's cp1252 console, raising
UnicodeEncodeError, not a Torch/CUDA or AI-model error.

V286 makes the worker failure self-test print ASCII-escaped JSON, which
remains a lossless Unicode representation when parsed. It does not change
Gradio labels, the local UTF-8 logs, the worker failure schema, the image
engine, or any existing button. Two regression tests cover strict cp1252.

Acceptance: full Windows CI, frozen failure self-test, extracted ZIP
verification. This does not prove real SD1.5 image inference.
