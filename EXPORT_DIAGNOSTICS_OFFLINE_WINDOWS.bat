@echo off
setlocal
cd /d "%~dp0"
if not exist "logs" mkdir "logs"
echo BIMAI360 - CHAN DOAN OFFLINE / Khong can Gradio
if exist "BIMAI360.exe" (
  "BIMAI360.exe" --diagnostics
) else (
  if exist "python\python.exe" (
    "python\python.exe" run_portable.py --diagnostics
  ) else (
    py -3 run_portable.py --diagnostics
  )
)
echo.
echo Ket qua / Results: "%CD%\logs"
echo Neu that bai, mo logs\startup_console.log va logs\startup_error.log
pause
