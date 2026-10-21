@echo off
setlocal
cd /d "%~dp0"
if not exist "runtime\active_python.txt" (
  echo [ERROR] Run the environment setup on the build machine first.
  exit /b 1
)
set /p PYTHON=<"runtime\active_python.txt"
"%PYTHON%" -m learning.data_quality --manifest "dataset\manifest_v71.jsonl" --root "dataset\raw" --out "dataset\quality_v71.json"
if errorlevel 1 (
  echo [BLOCKED] Review dataset\quality_v71.json before training.
  exit /b 2
)
echo [PASS] Dataset audit passed; this does not mean the model is trained.
