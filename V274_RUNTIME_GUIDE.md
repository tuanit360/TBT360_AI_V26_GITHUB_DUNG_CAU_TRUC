# V274 — alternative Windows launch profiles

These profiles reuse exactly the same existing Gradio UI and command registry.
They do not remove or rename any buttons. None is a substitute for real Windows
hardware/browser smoke tests.

## A: frozen CPU portable
Keep running BIMAI360.exe from the extracted CPU portable artifact, never from
inside ZIP. For offline diagnostics run START_BIMAI360_SAFE_DIAGNOSTICS.bat.
The current CI builds and tests this Windows CPU profile.

## B: Python 3.11 VENV (avoid PyInstaller)
From an extracted repository directory:
```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu
.venv\Scripts\python.exe -m pip install -r requirements-runtime.txt
.venv\Scripts\python.exe -m pip check
```
Run START_BIMAI360_VENV.bat. It stops with a JSON error before launching if
Python packages are absent or the port is already bound.

## C: Safe diagnostics (NOT a full BIM UI)
START_BIMAI360_SAFE_DIAGNOSTICS.bat collects diagnostics without starting
Gradio, model inference, LoRA or the BIM user interface. It does not claim
that CAD/BIM functionality is available while the application server is down.

## D: CUDA troubleshooting only
Run preflight with --profile cuda. This checks only for NVIDIA driver tooling;
it does not prove CUDA device suitability, successful model loading, 4 GiB
VRAM, successful SD1.5 generation, or license entitlement.

## Shared expectations
- Only local port 7861 is probed; close stale instances before launching.
- The preflight JSON is stored under logs and deliberately omits environment
  secrets, model paths and detailed identifiers.
- Missing dependencies are reported; no silent pip installation occurs.
- CI passing cannot validate specific customer GPU/browser configurations.
