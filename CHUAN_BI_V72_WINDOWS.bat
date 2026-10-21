@echo off
setlocal
cd /d "%~dp0"
if not exist "runtime\active_python.txt" (echo [ERROR] Run setup on build machine first.& exit /b 1)
set /p PYTHON=<"runtime\active_python.txt"
"%PYTHON%" -m training.gated_dataset --manifest dataset\manifest_v71.jsonl --root dataset\raw --output dataset\v72_certified
if errorlevel 1 exit /b 1
"%PYTHON%" -m training.gated_dataset --output dataset\v72_certified --verify
pause
