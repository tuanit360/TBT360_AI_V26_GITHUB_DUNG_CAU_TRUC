@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python 3.11 isolated environment is missing.
  echo Run: py -3.11 -m venv .venv
  echo Then install CPU PyTorch and requirements-runtime.txt as described in V274_RUNTIME_GUIDE.md
  pause
  exit /b 2
)
if not exist "logs" mkdir "logs"
".venv\Scripts\python.exe" -m tools.runtime_preflight --root . --profile venv --output "logs\preflight-v274-venv.json"
if errorlevel 1 (
  echo Environment preflight failed; open logs\preflight-v274-venv.json
  pause
  exit /b 2
)
set "NO_PROXY=127.0.0.1,localhost,::1,%NO_PROXY%"
".venv\Scripts\python.exe" run_portable.py > "logs\venv_console.log" 2>&1
set "RESULT=%ERRORLEVEL%"
type "logs\venv_console.log"
pause
exit /b %RESULT%
