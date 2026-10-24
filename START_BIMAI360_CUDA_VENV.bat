@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-cuda\Scripts\python.exe" (
  echo [LOI] Chua co CUDA VENV rieng: .venv-cuda
  echo Xem V275_RUNTIME_GUIDE.md de tao moi truong PyTorch CUDA.
  pause
  exit /b 2
)
if not exist "logs" mkdir "logs"
".venv-cuda\Scripts\python.exe" -c "import torch,sys; print('torch',torch.__version__,'CUDA build',torch.version.cuda); sys.exit(0 if torch.version.cuda and torch.cuda.is_available() else 2)"
if errorlevel 1 (
  echo [LOI] PyTorch CUDA chua hoat dong. Khong khoi dong sai che do.
  pause
  exit /b 2
)
set "BIMAI360_FORCE_CPU=0"
set "NO_PROXY=127.0.0.1,localhost,::1,%NO_PROXY%"
".venv-cuda\Scripts\python.exe" run_portable.py > "logs\cuda_venv_console.log" 2>&1
set "RESULT=%ERRORLEVEL%"
type "logs\cuda_venv_console.log"
pause
exit /b %RESULT%
