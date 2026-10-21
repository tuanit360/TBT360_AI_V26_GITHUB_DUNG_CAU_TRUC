@echo off
setlocal
cd /d "%~dp0"
set "TBT360_OFFLINE=1"
if exist TBT360_AI.exe (
  TBT360_AI.exe
) else if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe run_portable.py
) else (
  echo [ERROR] No compiled EXE or build virtualenv exists.
  exit /b 1
)
