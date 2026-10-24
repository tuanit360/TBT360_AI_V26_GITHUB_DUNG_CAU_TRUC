# BIMAI360 V275 — CPU/CUDA selection and separate runtimes

The current Gradio tabs and controls remain unchanged. V275 does not introduce
a new UI or mutate BIM data as part of runtime selection.

## CPU Portable
Use the existing GitHub Actions CPU ZIP and run
CHAY_BIMAI360_CPU_KHONG_CUDA.bat. The CPU wheel **does not** enable CUDA even
when NVIDIA drivers are installed. CPU model inference requires sufficient
available physical RAM; the application fails safely below 7 GiB.

## CUDA VENV (separate from CPU Portable)
On Windows with a compatible NVIDIA driver, create a fresh Python 3.11 VENV:
```powershell
py -3.11 -m venv .venv-cuda
.venv-cuda\Scripts\python.exe -m pip install --upgrade pip
.venv-cuda\Scripts\python.exe -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
.venv-cuda\Scripts\python.exe -m pip install -r requirements-runtime.txt
.venv-cuda\Scripts\python.exe -m pip check
```
Before running, inspect the active NVIDIA driver and CUDA compatibility.
Run START_BIMAI360_CUDA_VENV.bat from the source directory.
CUDA mode is refused unless installed PyTorch both contains CUDA support
and reports an accessible GPU.

## Automatic selection
- CUDA PyTorch + usable GPU: CUDA (with existing 4-GiB offload controls).
- Missing/unusable CUDA and >= 7 GiB available RAM: CPU with a clear reason.
- No CUDA and < 7 GiB available RAM: reject before loading model.
- GPU placement failure: evict CUDA instance, then recheck CPU RAM before
  building a fresh CPU pipeline; do not reuse the half-initialized pipeline.
- Reference images, BIM state and diagnostic logs are untouched.

This does not promise AI output without a valid model/checkpoint, or claim
GPU/real-image tests passed on CI's CPU-only Windows runner.
