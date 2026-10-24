@echo off
setlocal
cd /d "%~dp0"
if not exist "logs" mkdir "logs"
echo === BIMAI360 V274 PRE-FLIGHT ===
if exist "python\python.exe" (
  "python\python.exe" -m tools.runtime_preflight --root . --profile cpu --output "logs\preflight-v274.json"
) else (
  if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m tools.runtime_preflight --root . --profile venv --output "logs\preflight-v274.json"
  ) else (
    py -3.11 -m tools.runtime_preflight --root . --profile cpu --output "logs\preflight-v274.json"
  )
)
set "RESULT=%ERRORLEVEL%"
echo Report: logs\preflight-v274.json
pause
exit /b %RESULT%
