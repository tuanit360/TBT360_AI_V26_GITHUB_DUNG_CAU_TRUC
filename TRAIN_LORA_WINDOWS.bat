@echo off
setlocal
cd /d "%~dp0"
if not exist "runtime\active_python.txt" (
  echo [ERROR] First set up Python on the BUILD machine.
  pause
  exit /b 1
)
set /p PYTHON=<"runtime\active_python.txt"
if not exist "dataset\manifest_v71.jsonl" (
  echo [BLOCKED] Dataset manifest missing: dataset\manifest_v71.jsonl
  pause
  exit /b 1
)
"%PYTHON%" -m training.gated_dataset --manifest dataset\manifest_v71.jsonl --root dataset\raw --output dataset\v72_certified
if errorlevel 1 goto fail
"%PYTHON%" -m training.gated_dataset --output dataset\v72_certified --verify
if errorlevel 1 goto fail
"%PYTHON%" -m training.run_lora --name tbt360_architecture_v72 --steps 300
if errorlevel 1 goto fail
echo [OK] Training completed. Check validation before approving any checkpoint.
pause
exit /b 0
:fail
echo [BLOCKED] No new trained model has been approved.
pause
exit /b 1
