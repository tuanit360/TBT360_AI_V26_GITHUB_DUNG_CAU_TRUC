@echo off
setlocal
cd /d "%~dp0"
echo Safe diagnostic mode: no Gradio, Torch, Diffusers, LoRA or AI inference
if exist "BIMAI360.exe" (
  "BIMAI360.exe" --diagnostics
) else (
  if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run_portable.py --diagnostics
  ) else (
    py -3.11 run_portable.py --diagnostics
  )
)
set "RESULT=%ERRORLEVEL%"
echo Safe-mode diagnostics finished with code %RESULT%.
echo Diagnostics ZIP should be in logs folder.
pause
exit /b %RESULT%
