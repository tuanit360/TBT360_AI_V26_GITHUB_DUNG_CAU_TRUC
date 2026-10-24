# V283 Frozen worker transport gate

This test launches a **separate OS process**, either by invoking the same
PyInstaller EXE with --worker-transport-probe or by using a separate Python
module in source mode. The worker writes a real PNG, ZIP and JSON. The
parent verifies CRC, image bytes and SHA256. It does **not** load SD1.5 or
claim AI inference occurred. It specifically tests that frozen child dispatch
works and that files can cross the process boundary.

On Windows, run `BIMAI360.exe --worker-transport-self-test` from the
extracted portable folder. The CI workflow now runs it on the packaged EXE.
A pass means worker transport is available, NOT that a CUDA/CPU model is
available. Existing Gradio UI and generation controls are unchanged.
