@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
echo [BIMAI360] Configure separate CUDA environment for NVIDIA T600 4GB.
echo [BIMAI360] This does not modify the packaged CPU Portable executable.
py -3.11 -m venv .venv-t600-cuda
if errorlevel 1 goto :fail
set "PY=.venv-t600-cuda\Scripts\python.exe"
"%PY%" -m pip install --upgrade "pip<27" "setuptools<85" wheel
if errorlevel 1 goto :fail
"%PY%" -m pip install torch==2.5.1+cu121 torchvision==0.20.1+cu121 --index-url https://download.pytorch.org/whl/cu121
if errorlevel 1 goto :fail
rem The real LoRA trainer also imports datasets, TensorBoard and ftfy.
rem Runtime-only requirements are insufficient for real training.
"%PY%" -m pip install -r requirements.txt
if errorlevel 1 goto :fail
"%PY%" -m pip install "ftfy>=6.1,<7"
if errorlevel 1 goto :fail
"%PY%" -m pip check
if errorlevel 1 goto :fail
"%PY%" -c "import torch,sys; print('torch',torch.__version__,'CUDA build',torch.version.cuda); print('CUDA available:',torch.cuda.is_available()); sys.exit(0 if torch.cuda.is_available() else 2)"
if errorlevel 1 goto :fail
"%PY%" -m training.local_hardware_diagnostic
if errorlevel 1 goto :fail
echo [BIMAI360] CUDA Python environment ready. Training and inference NOT yet verified.
echo [BIMAI360] Use .venv-t600-cuda\Scripts\python.exe with training modules.
exit /b 0
:fail
echo [BIMAI360] CUDA environment installation/validation failed. No GPU success claimed.
exit /b 1
